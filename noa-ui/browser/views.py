import requests
from datetime import datetime
import json

from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection

from utils.geo_utils import bbox_to_polygon

from django.core.serializers.json import DjangoJSONEncoder

API_BASE_URL = "http://10.201.40.192:30080/api/SatelliteProduct/GetAll"
API_URL =  "http://10.201.40.192:30080/api"

def map_view(request):
    return render(request, 'base.html')

def search(request):
    if request.method == "POST":
        data_source = request.POST.get("data_source")
        start_date = request.POST.get("start_date") + "T00:00:00.000"
        end_date = request.POST.get("end_date", datetime.now().strftime("%Y-%m-%d"))
        geometry = request.POST.get("bbox")
        cloud_coverage = request.POST.get("cloud_coverage", None)
        product_type = request.POST.get("product_type", None)
        relative_orbit = request.POST.get("relative_orbit", None)

        geometry = [coordinate for coordinate in geometry.split(",")]

        if data_source == "Sentinel-2":
            payload = {
                "provider": 2, 
                "startDate": start_date,
                "geometry": bbox_to_polygon(geometry),
                "properties": {
                    "cloudCoverage": cloud_coverage
                },
            }
            endpoint = f"{API_BASE_URL}/SatelliteProduct"
        
        elif data_source == "Sentinel-1":
            payload = {
                "provider": 1,  
                "startDate": start_date,
                "geometry": bbox_to_polygon(geometry),
                "properties": {
                    "productType": product_type,
                    "relativeOrbit": relative_orbit,
                },
            }
            endpoint = f"{API_BASE_URL}/SatelliteProduct"

        
        else:
            return JsonResponse({"error": "Invalid data source"}, status=400)

        try:
            response = requests.post(endpoint, json=payload, verify=False) 
            response.raise_for_status()
        
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": str(e)}, status=500)

        return JsonResponse(response.json())

    return render(request, "search.html")


def results(request):
    """
    Handles the form submission, queries `pgstac`, and renders results.
    """
    if request.method == 'POST':

        start_date = request.POST.get('start_date').split('T')[0]
        end_date = request.POST.get('end_date')
        bbox = request.POST.get('bbox')

        try:
            bbox_coords = [float(coord) for coord in bbox.split(',')]
            
            if len(bbox_coords) != 4:
                raise ValueError("Bounding box must have exactly 4 coordinates.")
        
        except ValueError as e:
            return render(request, 'base.html', {'error': f"Invalid bounding box: {str(e)}"})

        all_products = _collect_existing_products(start_date, end_date, bbox)


        query = """
            SELECT id, ST_AsGeoJSON(ST_Transform(geometry, 4326)), content, datetime
            FROM pgstac.items
            WHERE datetime >= %s
              AND datetime <= %s
              AND ST_Intersects(geometry, ST_MakeEnvelope(%s, %s, %s, %s, 4326))
        """
        params = [start_date, end_date, bbox_coords[0], bbox_coords[1], bbox_coords[2], bbox_coords[3]]

        existing_items = []
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            unique_names = []
            for row in rows:
                item_id = row[0]
                geometry = json.loads(row[1]) 
                content = json.loads(row[2])  
                
                content['geometry'] = geometry
                
                existing_items.append({
                    "id": item_id,
                    "geometry": geometry,
                    "properties": content.get('properties', {}),
                    "assets": content.get('assets', {}),
                })

                unique_names.append(content.get('properties').get('s2:product_uri'))
        
        not_available = [] 
        
        for product in all_products:
            
            if product['name'] in unique_names:
                continue
            
            not_available.append(product)

        return render(request, 'results.html', {"items": {"available_items": existing_items, "not_available_items":not_available}})

    return render(request, 'base.html')



def _collect_existing_products(start_date, end_date, bbox, cloud_cover=100, provider=2, satellite_collection=1):
    geometry = [float(coordinate) for coordinate in bbox.split(",")]
    polygon = _bbox_to_polygon(geometry[0],geometry[1],geometry[2],geometry[3])
    
    payload = {
        "provider": int(provider),
        "startDate": start_date,
        "endDate": end_date,
        "satelliteCollection": satellite_collection,
        "cloudCover": int(cloud_cover),
        "geometry": polygon,
        "properties": {},
    }

    try:
        response = requests.post(API_BASE_URL, json=payload)
        response.raise_for_status() 
        results = response.json()
        
        for result in results:
            result['tile'] = result['name'].split('_')[5]
            result['sensing_date'] = result['name'].split('_')[2][:4] + '-' + result['name'].split('_')[2][4:6] + '-' + result['name'].split('_')[2][6:8]
            result['quicklook'] = f"https://datahub.creodias.eu/odata/v1/Assets({result['uuid']})/$value"
        return results
    except requests.RequestException as e:
        return JsonResponse({"error": f"API request failed: {str(e)}"}, status=500)

def _bbox_to_polygon(xmin, ymin, xmax, ymax):
    polygon = {
        "type": "string",
        "coordinates": [[
            [xmin, ymin],  
            [xmax, ymin],  
            [xmax, ymax],  
            [xmin, ymax], 
            [xmin, ymin]  
        ]]
    }
    return polygon


def submit_order(request):
    if request.method == 'POST':
        item_ids_json = request.POST.get('item_ids', '[]')
        item_ids = json.loads(item_ids_json)
        
        payload = {
            "orderType": 1, 
            "productIds": item_ids
        }

        api_url = f"{API_URL}/Orders"
        try:
            response = requests.post(api_url, json=payload, headers={"Content-Type": "application/json"})

            if response.status_code == 200:
                return JsonResponse({"message": "Order successfully submitted", "data": response.json()})
            
            else:
                return JsonResponse({
                    "error": "Failed to submit order",
                    "status_code": response.status_code
                }, status=400)

        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": str(e)}, status=500)
    