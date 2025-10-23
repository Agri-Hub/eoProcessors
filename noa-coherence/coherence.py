import os,sys
import datetime as dt
import argparse

# Change the path below
sys.path.append('/home/<USER>/.snap/snap-python')

from snappy import GPF
from snappy import ProductIO
from snappy import HashMap
from snappy import jpy
from snappy import WKTReader
from snappy import File
from snappy import ProgressMonitor
from time import sleep
import gc


def read(filename):
    reader = ProductIO.getProductReader('SENTINEL-1')
    
    return reader.readProductNodes(filename,None)

def write(product, filename):
    ProductIO.writeProduct(product, filename, "GeoTIFF")


def topsar_split(product, swath: str, pol: str):
    """
    Splits a TOPSAR product into subswaths and polarizations.

    Parameters:
    product: The input TOPSAR product.
    swath (str): The subswath to process (e.g., 'IW1', 'IW2', 'IW3').
    pol (str): The polarization to select (e.g., 'VV', 'VH').

    Returns:
    Product: The split product.
    """
    parameters = HashMap() 
    parameters.put('subswath', swath)
    parameters.put('selectedPolarisations', pol)
    
    return GPF.createProduct("TOPSAR-Split", parameters, product)

def topsar_merge(product, pol: str):
    """
    Merges split TOPSAR products.

    Parameters:
    product: The input product.
    pol (str): The polarization to select.

    Returns:
    Product: The merged product.
    """
    parameters = HashMap()
    parameters.put('selectedPolarisations', pol)
    
    return GPF.createProduct("TOPSAR-Merge", parameters, product)


def apply_orbit_file(product, mode: int):
    """
    Applies orbit file corrections to the product.

    Parameters:
    product: The input product.
    mode (int): Orbit file mode (1 for Restituted, else Precise).

    Returns:
    Product: The orbit-corrected product.
    """
    parameters = HashMap()
    
    if mode == 1:
        parameters.put("Orbit State Vectors", "Sentinel Restituted (Auto Download)")
    else:
        parameters.put("Orbit State Vectors", "Sentinel Precise (Auto Download)")
    
    parameters.put("Polynomial Degree", 3)
    
    return GPF.createProduct("Apply-Orbit-File", parameters, product)

def back_geocoding(product):
    """
    Performs back-geocoding on the product.

    Parameters:
    product: The input product.

    Returns:
    Product: The back-geocoded product.
    """
    parameters = HashMap()
    parameters.put("Digital Elevation Model", "SRTM 1Sec HGT (Auto Download)")
    parameters.put("DEM Resampling Method", "NEAREST_NEIGHBOUR")
    parameters.put("Resampling Type", "BICUBIC_INTERPOLATION")
    parameters.put("Mask out areas with no elevation", True)
    parameters.put("Output Deramp and Demod Phase", False)
    
    return GPF.createProduct("Back-Geocoding", parameters, product)

def topsar_deburst(product, pol: str):
    """
    Removes burst overlaps from TOPSAR products.

    Parameters:
    product: The input product.
    pol (str): The polarization to process.

    Returns:
    Product: The debursted product.
    """
    parameters = HashMap()
    parameters.put("Polarisations", pol)
    return GPF.createProduct("TOPSAR-Deburst", parameters, product)

def coherence_generation(product):
    """
    Generates coherence from the product.

    Parameters:
    product: The input product.

    Returns:
    Product: The coherence product.
    """
    parameters = HashMap()
    parameters.put("Subtract flat-earth phase", True)
    parameters.put("Degree of \"Flat Earth\" polynomial", 5)
    parameters.put("Number of \"Flat Earth\" estimation points", 501)
    parameters.put("Orbit interpolation degree", 3)
    parameters.put("Include coherence estimation", True)
    parameters.put("Square Pixel", True)
    parameters.put("Independent Window Sizes", False)
    parameters.put("Coherence Azimuth Window Size", 3)
    parameters.put("Coherence Range Window Size", 10)
    return GPF.createProduct("Coherence", parameters, product)

def write_snaphu(product, filename):
    ProductIO.writeProduct(product, filename, "Snaphu")



def geometric_correction(product, polarisation: str, to_print: bool = True):
    """
    Performs geometric correction on the product.

    Parameters:
    product: The input product.
    polarisation (str): The polarization to process.
    to_print (bool): Whether to print band names.

    Returns:
    Product: The geometrically corrected product.
    """
    parameters = HashMap()
    parameters.put('demName', 'SRTM 1Sec HGT')# 'SRTM 3Sec')  # SRTM 1Sec HGT
    parameters.put('externalDEMNoDataValue', 0.0)
    parameters.put('demResamplingMethod', "BILINEAR_INTERPOLATION")
    parameters.put('imgResamplingMethod', "BILINEAR_INTERPOLATION")
    parameters.put("Mask out areas with no elevation", True)
    parameters.put('sourceBands', list(speckle.getBandNames())[0])
    parameters.put('nodataValueAtSea', False)
    parameters.put('pixelSpacingInMeter', 10.0)
    parameters.put('mapProjection',"WGS84(DD)")
    terrain = GPF.createProduct('Terrain-Correction', parameters, speckle)
    if to_print:
        print("Bands:   %s" % (list(terrain.getBandNames())))
    return terrain

def subset(product, bbox: list, to_print: bool = True):
    """
    Subsets the product using a bounding box.

    Parameters:
    product: The input product.
    bbox (list): Bounding box coordinates [min_lon, min_lat, max_lon, max_lat].
    to_print (bool): Whether to print band names.

    Returns:
    Product or None: The subsetted product or None if no bands.
    """
    parameters = HashMap()
    min_lon, min_lat, max_lon, max_lat = bbox[0], bbox[1], bbox[2], bbox[3]
    wkt_polygon = f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    geom = WKTReader().read(wkt_polygon)
    parameters.put('copyMetadata', True)
    parameters.put('geoRegion', geom)
    subset = GPF.createProduct('Subset', parameters, product)
    
    if to_print:
        print("Bands:   %s" % (list(subset.getBandNames())))
    if len(list(subset.getBandNames())) == 0:
        return None
    else:
        return subset


def subset_with_bbox(source_product, min_lon: float, min_lat: float, max_lon: float, max_lat: float):
    """
    Subsets the product using specified bounding box coordinates.

    Parameters:
    source_product: The input product.
    min_lon (float): Minimum longitude.
    min_lat (float): Minimum latitude.
    max_lon (float): Maximum longitude.
    max_lat (float): Maximum latitude.

    Returns:
    Product: The subsetted product.
    """
    parameters = HashMap()
    wkt = f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    geom = WKTReader().read(wkt)
    parameters.put('copyMetadata', True)
    parameters.put('geoRegion', geom)
    subset_product = GPF.createProduct('Subset', parameters, source_product)
    return subset_product


def insar_pipeline(filename_1: str, filename_2: str, outpath: str, bbox: list, selectedPol: list):
    """
    Main InSAR processing pipeline for Sentinel-1 data.

    Parameters:
    master (str): Path to the master image.
    slave (str): Path to the slave image.
    outpath (str): Output directory path.
    event_id (str): Event identifier.
    bbox (list): Bounding box coordinates [min_lon, min_lat, max_lon, max_lat].
    other_param: Additional parameter for processing.
    """
    for pol in selectedPol:
        product_1 = read(filename_1)
        product_2 = read(filename_2)

        swaths = ['IW1', 'IW2', 'IW3']
        ind = 0
        final_products = []
        failedPreprocessing = False
        for swath in swaths:
            try:
                print('TOPSAR-Split')
                product_TOPSAR_1 = topsar_split(product_1, swath, pol)
                product_TOPSAR_2 = topsar_split(product_2, swath, pol)
            except Exception as e:
                print(e)
                failedPreprocessing = True
                break
            product_orbitFile_1 = apply_orbit_file(product_TOPSAR_1,2)
            product_orbitFile_2 = apply_orbit_file(product_TOPSAR_2,2)

            backGeocoding = back_geocoding([product_orbitFile_1, product_orbitFile_2])
            coherence = coherence_generation(backGeocoding)
            TOPSAR_deburst = topsar_deburst(coherence, pol)
            final_products.append(TOPSAR_deburst)

        if failedPreprocessing:
            return

        merged = topsar_merge(final_products, pol)
        terrain = geometric_correction(merged, pol)
        band_names = list(terrain.getBandNames())

        extension = f"{band_names[0]}_{str(pol)}_buffer0_window10_clipped.tif"
		
        output = os.path.join(outpath, extension)
        

        subset_data = subset(terrain,bbox) 
        tmp = os.path.join(output)
        parameters = HashMap()
        parameters.put('file', tmp)
        parameters.put('formatName', 'GeoTIFF')
        
        if not os.path.exists(output):
            WriteOp = jpy.get_type('org.esa.snap.core.gpf.common.WriteOp')
            w = WriteOp(subset_data, File(tmp), 'GeoTIFF')
            w.writeProduct(ProgressMonitor.NULL)
        
        subset_data.dispose()
        terrain.dispose()
        product_1.dispose()
        product_2.dispose()
        product_TOPSAR_1.dispose()
        product_TOPSAR_2.dispose()
        product_orbitFile_2.dispose()
        product_orbitFile_1.dispose()
        backGeocoding.dispose()
        coherence.dispose()
        TOPSAR_deburst.dispose()
        merged.dispose()
        gc.collect()


def main():
    """
    Main function to process Sentinel-1 data using the SNAP toolbox via snappy.
    """
   
    parser = argparse.ArgumentParser(description='Process Sentinel-1 data using SNAP.')
    parser.add_argument('master', help='Path to the master image')
    parser.add_argument('slave', help='Path to the slave image')
    parser.add_argument('outpath', help='Output path')
    parser.add_argument('bbox', nargs=4, type=float,
                        help='Bounding box coordinates: [minLon, minLat, maxLon, maxLat]')

    # TODO add the polarizations as parameter
    pols = ['VH','VV'] 
    
    args = parser.parse_args()
    
    # Extract arguments
    master = args.master
    slave = args.slave
    outpath = args.outpath
    bbox = args.bbox  
    
    insar_pipeline(master, slave, outpath,bbox,pols)


if __name__ == "__main__":
    main()



