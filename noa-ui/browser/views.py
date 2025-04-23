import requests
import json
import os
import re
from django.http import HttpResponse, Http404
from sentinel_browser.settings import STATIC_ROOT
from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView
from django.urls import reverse_lazy
from browser.forms import RegisterForm, NoaUserCreationForm

# from utils.geo_utils import bbox_to_polygon

# from django.core.serializers.json import DjangoJSONEncoder

API_BASE_URL = "http://10.201.40.192:30080/api/SatelliteProduct/GetAll"
API_URL = "http://10.201.40.192:30080/api"


from django.templatetags.static import static



class RegisterView(CreateView):
    form_class = NoaUserCreationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("login")


def proxy_quicklook(request, uuid):
    """
    Serve the quicklook from catalogue.dataspace,
    falling back to a local placeholder on error.
    """
    catalogue_url = (
        f"https://catalogue.dataspace.copernicus.eu/"
        f"odata/v1/Assets({uuid})/$value"
    )
    try:
        # requests follows 301→download.dataspace for us by default
        resp = requests.get(catalogue_url, headers={"Accept": "image/jpeg"}, timeout=5)
        if resp.status_code == 200:
            # serve the real JPEG
            return HttpResponse(
                resp.content,
                content_type=resp.headers.get("Content-Type", "image/jpeg"),
            )
    except requests.RequestException:
        # network errors, timeouts, DNS failures, etc.
        pass

    if resp and resp.status_code == 200:
        return HttpResponse(resp.content, content_type=resp.headers.get("Content-Type", "image/jpeg"))

    return HttpResponse(None, content_type="image/png")


def map_view(request):
    return render(request, 'base.html')


@login_required
def results(request):
    """
    Handles the form submission, queries `pgstac`, and renders results.
    """
    if request.method == 'POST':

        start_date = request.POST.get('start_date').split('T')[0]
        end_date = request.POST.get('end_date')
        bbox = request.POST.get('bbox')

        cloud_cover, product_type = None, None

        if request.POST.get('dataSource') == "Sentinel-2":
            cloud_cover = request.POST.get('cloudCoverage')
            satellite_collection = 1
        else:
            product_type = request.POST.get('productType') 
            satellite_collection = 0

        try:
            bbox_coords = [float(coord) for coord in bbox.split(',')]

            if len(bbox_coords) != 4:
                raise ValueError("Bounding box must have exactly 4 coordinates.")

        except ValueError:
            return render(request, 'base.html', {'error': "Invalid bounding box"})

        # TODO introduce at least the cloud cover and satellite collection vars
        all_products = _collect_existing_products(start_date, end_date, bbox, cloud_cover= cloud_cover, product_type = product_type, satellite_collection=satellite_collection)

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

            # TODO review the following. What is your intent? Maybe a warning log message is enough?
            try:
                if product['name'] in unique_names:
                    continue
            except Exception:
                continue

            not_available.append(product)

        return render(request, 'results.html', {"items": {"available_items": existing_items, "not_available_items": not_available}})

    return render(request, 'base.html')


def _collect_existing_products(start_date, end_date, bbox, cloud_cover=None, product_type=None, provider=2, satellite_collection=1):
    geometry = [float(coordinate) for coordinate in bbox.split(",")]
    polygon = _bbox_to_polygon(geometry[0], geometry[1], geometry[2], geometry[3])

    print("Cloud:",cloud_cover)

    if satellite_collection == 1:
        payload = {
            "provider": int(provider),
            "startDate": start_date,
            "endDate": end_date,
            "satelliteCollection": satellite_collection,
            "cloudCover": int(cloud_cover),
            "geometry": polygon,
            "properties": {},
        }
    
    else:
         payload = {
            "provider": int(provider),
            "startDate": start_date,
            "endDate": end_date,
            "satelliteCollection": satellite_collection,
            "productType": product_type,
            "geometry": polygon,
            "properties": {},
        }        

    try:
        response = requests.post(API_BASE_URL, json=payload)
        response.raise_for_status() 
        product_results = response.json()
        
        if satellite_collection == 1:
            for result in product_results:
                result['tile'] = result['name'].split('_')[5]
                result['sensing_date'] = result['name'].split('_')[2][:4] + '-' + result['name'].split('_')[2][4:6] + '-' + result['name'].split('_')[2][6:8]
                result['quicklook'] = f"https://datahub.creodias.eu/odata/v1/Assets({result['uuid']})/$value"
        
        elif satellite_collection == 0:
            # 'name': 'S1A_IW_SLC__1SDV_20231217T163246_20231217T163314_051697_063E38_8102.SAFE', 
            for result in product_results:
                tmp = result['name'].split('_')[5][:8]
                result['sensing_date'] = tmp[:4] + '-' + tmp[4:6] + '-' + tmp[6:8]
                result['quicklook'] = f"https://datahub.creodias.eu/odata/v1/Assets({result['uuid']})/$value"
                
                _orbit_number = re.search(r'_(\d{6})_', result['name']).group(1)
                _acquisition_start_time = re.search(r'_(\d{8}T\d{6})_', result['name']).group(1)
                _hour = int(_acquisition_start_time[9:11])
                _asc_desc = 'Ascending' if 6 <= _hour < 18 else 'Descending'

                result['tile'] = f"{_orbit_number}_{_asc_desc}"


        return product_results

    except requests.RequestException:
        return JsonResponse({"error": "API request failed}"}, status=500)


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


@login_required
def submit_order(request):
    if request.method == 'POST':
        item_ids_json = request.POST.get('item_ids', '[]')
        item_ids = json.loads(item_ids_json)

        order_type = request.POST.get("order_type")

        print("Order type:", order_type)

        payload = {
            "orderType": int(order_type),
            "productIds": item_ids
        }

        api_url = f"{API_URL}/Orders"

        try:
            response = requests.post(api_url, json=payload, headers={"Content-Type": "application/json"})

            if response.status_code == 200:
                order_id = response.json()

                update_json_file(order_id, item_ids, order_type)

                return render(request, 'dashboard.html', {"message": "Order successfully submitted!"})

            return JsonResponse({
                "error": "Failed to submit order",
                "status_code": response.status_code
            }, status=400)

        except requests.exceptions.RequestException:
            return JsonResponse({"error": "Internal error"}, status=500)


@login_required
def user_dashboard(request, file_path="responses.json"):

    try:    
        with open(file_path, "r") as json_file:
            data = json.load(json_file)
            user_orders = list(data.keys())
    
    except json.JSONDecodeError:
        user_orders = []
        print("JSON file is empty or corrupted.")

    api_base_url = "http://10.201.40.192:30080/api/Orders/"

    order_statuses = []

    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')


    for order_id in user_orders:
        try:
            response = requests.get(f"{api_base_url}{order_id}")

            response.raise_for_status()

            status = response.json()

            order_statuses.append({
                "order_id": order_id,
                "status": "Completed" if status else "In Progress"
            })
        
        except requests.RequestException:
            order_statuses.append({
                "order_id": order_id,
                "status": "Error fetching status"
            })

        if search_query:
            order_statuses = [order for order in order_statuses if search_query in order["order_id"]]

        if status_filter in ["0", "1"]:
            order_statuses = [order for order in order_statuses if order["status"] == "Completed" and status_filter == "1" or order["status"] == "In Progress" and status_filter == "0"]

    return render(request, "dashboard.html", {"order_statuses": order_statuses})


def update_json_file(response_data, product_ids, order_type, file_path="responses.json"):
    """
    Updates a JSON file with new key-value pairs in the format:
    {
        "order-id": {
            "product-ids": [...],
            "order-type": "..."
        }
    }

    :param response_data: The order ID (key).
    :param product_ids: The list of product IDs associated with the order.
    :param order_type: The type of order.
    :param file_path: The path to the JSON file (default is 'responses.json').
    """
    data = {}

    if os.path.exists(file_path):
        with open(file_path, "r") as json_file:
            try:
                data = json.load(json_file)
            except json.JSONDecodeError:
                print("Existing JSON file is empty or corrupted. Starting fresh.")

    data[response_data] = {
        "product-ids": product_ids,
        "order-type": order_type
    }

    print("Data:",data)

    with open(file_path, "w") as json_file:
        json.dump(data, json_file, indent=4)

    print(f"Updated JSON file: {file_path}")
