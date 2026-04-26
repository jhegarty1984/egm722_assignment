import os

# Define Project Database
os.environ['PROJ_LIB'] = r'C:\Users\hegar\anaconda3\envs\egm722_assignment\Library\share\proj'

import shapely
import pandas as pd
import geopandas as gpd
import numpy as np
import rasterio as rio
import cartopy.crs as ccrs
import matplotlib.pyplot as plt

from rasterio.plot import show
from rasterio.features import shapes
from shapely.geometry import shape
from rasterio._warp import Resampling
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject

# Define the full file path to the Lough Nillan SAC shapefile
file_path_sac = r'C:\GIS_MSc\2026\EGM722_Programming_for_GIS&Remote_Sensing\Assignment\Spatial_Data\Lough_Nillan_SAC\lough_nillan_sac.shp'

# Load the vector data into a GeoDataFrame named 'sac'
sac = gpd.read_file(file_path_sac)

# Verify the data loaded correctly by printing the first few rows
print(sac.head())

# Check the coordinate reference system of the GeoDataFrame
print(sac.crs)

# Generate the minimum rotated rectangle that covers the sac
sac_area = sac.minimum_rotated_rectangle()

# a sign of 1 means oriented counter-clockwise
sac_geom = sac_area.geometry.iloc[0]
sac_area_oriented = shapely.geometry.polygon.orient(sac_geom, sign=1)

# Define the full file path to the Corrine Landcover raster data
file_path_clc = r'C:\GIS_MSc\2026\EGM722_Programming_for_GIS&Remote_Sensing\Assignment\Spatial_Data\Satellite_Data\corine_land_cover_2018\64554\Results\u2018_clc2018_v2020_20u1_raster100m\u2018_clc2018_v2020_20u1_raster100m\DATA\U2018_CLC2018_V2020_20u1.tif'

# Open the CLC dataset
with rio.open(file_path_clc) as src:
    # Read the data (band 1) as a NumPy array
    clc_data = src.read(1)

    # Access metadata important for clc (CRS is usually EPSG:3035)
    print(src.crs)

#Reproject CLC to ITM (CRS 2157)
def reproject_to_itm(file_path_clc, output_path='clc_itm', clc_itm=r'C:\GIS_MSc\2026\EGM722_Programming_for_GIS&Remote_Sensing\Assignment\Spatial_Data\assignment_output_data\clc_itm.tif'):
    dst_crs = 'EPSG:2157'

    with rio.open(file_path_clc) as src:
        # Calculate the transform and dimensions for the new CRS
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds)

        # Update metadata for the output file
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height
        })

        # Create the output file and perform the reprojection
        with rio.open(clc_itm, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rio.band(src, i),
                    destination=rio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest  # Use 'bilinear' or 'cubic' for continuous data
                )
    print(f"Reprojecting {file_path_clc} to {clc_itm}")

#Clip CLC to SAC
def clip_clc(file_path_clc, file_path_sac, output_path = 'clc_clipped', clc_clipped = r'C:\GIS_MSc\2026\EGM722_Programming_for_GIS&Remote_Sensing\Assignment\Spatial_Data\assignment_output_data\clc_clipped.tif'):
    # Load the SAC vector data
    sac_df = gpd.read_file(file_path_sac)

    # Open the raster data
    with rio.open(file_path_clc) as src:
        # Ensure the vector is in the same CRS as the raster
        vector_df = clc_clipped.to_crs(src.crs)

        # Get the geometry from the vector (mask expects a list of shapes)
        shapes = vector_df.geometry.values

        # Apply the mask/clip
        # crop=True clips the output extent to the bounds of the shapes
        out_image, out_transform = mask(src, shapes, crop=True)

        # Update the metadata for the new clipped file
        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })

        # Write the clipped raster to disk
        with rio.open(output_path, "w", **out_meta) as dest:
            dest.write(out_image)

# Extract Bog & Heath Habitats
def extract_habitats(clc_clipped, output_vector_path= 'peatland_habitats', peatland_habitats=r'C:\GIS_MSc\2026\EGM722_Programming_for_GIS&Remote_Sensing\Assignment\Spatial_Data\assignment_output_data\peatlands_habitats.shp'):
    # Codes for Bogs (412) and Heaths (322)
    target_codes = [412, 322]

    with rio.open(clc_clipped) as src:
        image = src.read(1)
        mask = np.isin(image, target_codes)

        # Convert identified pixels to a generator of shapes
        # We only want shapes where the mask is True (1)
        results = (
            {'properties': {'raster_val': v}, 'geometry': s}
            for i, (s, v) in enumerate(
            shapes(image, mask=mask, transform=src.transform)
        )
        )

        # Create a GeoDataFrame from the shapes
        geoms = list(results)
        gdf = gpd.GeoDataFrame.from_features(geoms, crs=src.crs)

        # Dissolve adjacent polygons of the same type (optional but recommended)
        gdf = gdf.dissolve(by='raster_val').reset_index()

        # Add a label column for clarity
        label_map = {412: "Peat Bog", 322: "Heathland"}
        gdf['habitat'] = gdf['raster_val'].map(label_map)

        # Save to Shapefile or GeoPackage
        gdf.to_file(peatland_habitats)
        print(f" Habitats saved to {peatland_habitats}")

# Define the full file path to the Sentinel-2 raster data

# Define the path to the specific band files (.jp2)
base_path_sen2 = r'C:\GIS_MSc\2026\EGM722_Programming_for_GIS&Remote_Sensing\Assignment\Spatial_Data\Satellite_Data\Sentinel_2_Data\S2A_MSIL2A_20250521.SAFE\S2A_MSIL2A_20250521.SAFE\GRANULE\L2A_T29UNA_A051772_20250521T114403\IMG_DATA\R10m'

# Specific band (Red, Green, Blue & NIR) file names
blue_path = base_path_sen2 + 'T29UNA_20250521T114401_B02_10m.jp2'
green_path = base_path_sen2 + 'T29UNA_20250521T114401_B03_10m.jp2'
red_path = base_path_sen2 + 'T29UNA_20250521T114401_B04_10m.jp2'
nearir_path = base_path_sen2 + 'T29UNA_20250521T114401_B08_10m.jp2'

# Calculate NDWI from Sentinel-2 raster data & create vector polygon of surface water bodies
def calculate_ndwi(green_path, nearir_path, output_path = 'ndwi_water_bodies', ndwi_water_bodies = r'C:\GIS_MSc\2026\EGM722_Programming_for_GIS&Remote_Sensing\Assignment\Spatial_Data\assignment_output_data\ndwi_water_bodies.shp', threshold = 0.2):
    # Open the Green (B3) and NIR (B8) bands
    with rio.open(green_path) as green_src, rio.open(nearir_path) as nearir_src:
        # Read the data as float32 to allow for decimal results and handle NaNs
        green = green_src.read(1).astype('float32')
        nir = nearir_src.read(1).astype('float32')

        # Ignore division by zero errors
        np.seterr(divide='ignore', invalid='ignore')

        # Calculate NDWI
        ndwi = (green - nir) / (green + nir)

        # Create a binary mask where NDWI > threshold
        # Values outside the threshold become 0, water becomes 1
        water_mask = (ndwi > threshold).astype('int16')

        # Vectorize the mask (only the '1' values)
        results = (
            {'properties': {'raster_val': v}, 'geometry': s}
            for i, (s, v) in enumerate(
            shapes(water_mask, mask=water_mask == 1, transform=green_src.transform)
        )
        )

        # 4. Convert to GeoDataFrame and dissolve into a single polygon
        gdf = gpd.GeoDataFrame.from_features(list(results), crs=green_src.crs)

        # Dissolve all individual polygons into one multipart polygon
        ndwi_water_polygon = gdf.dissolve()

        # Check the EPSG (prints the code, e.g., 32629)
        print(f"Current EPSG: {ndwi_water_polygon.crs.to_epsg()}")

        # Transform to EPSG 2157 (Irish Transverse Mercator)
        ndwi_water_polygon = ndwi_water_polygon.to_crs(epsg=2157)

        # Verify the transformation
        print(f"New EPSG: {ndwi_water_polygon.crs.to_epsg()}")

        # Clip the water bodies to the SAC boundary
        water_in_sac = ndwi_water_polygon.clip(sac)

        # Save output
        ndwi_water_polygon.to_file('ndwi_water.shp')
        print(f"Surface water polygon saved to {output_path}")

        # Save the clipped result
        water_in_sac.to_file('water_in_sac.shp')
        print("Clipped water bodies to SAC boundary.")

# Define the full file path to DEM raster data
dem_path = r'C:\GIS_MSc\2026\EGM722_Programming_for_GIS&Remote_Sensing\Assignment\Spatial_Data\Satellite_Data\corine_land_cover_2018\64554\Results\u2018_clc2018_v2020_20u1_raster100m\u2018_clc2018_v2020_20u1_raster100m\DATA\U2018_CLC2018_V2020_20u1.tif'


def extract_steep_slopes(dem_path, output_vector = 'steep_slopes', steep_slopes = r'C:\GIS_MSc\2026\EGM722_Programming_for_GIS&Remote_Sensing\Assignment\Spatial_Data\assignment_output_data\steep_slopes.shp', threshold_degrees=30):
    with rio.open(dem_path) as src:
        # Determine a suitable UTM CRS for the area to get units in meters
        # This is critical; calculating slope on degrees (EPSG:4326) yields wrong results.
        lon, lat = src.lnglat()
        utm_zone = int((lon + 180) / 6) + 1
        dst_crs = f'EPSG:326{utm_zone}' if lat > 0 else f'EPSG:327{utm_zone}'

        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds)

        # Reproject DEM to UTM
        dem_data = np.zeros((height, width), dtype='float32')
        reproject(
            rio.band(src, 1), dem_data,
            src_transform=src.transform, src_crs=src.crs,
            dst_transform=transform, dst_crs=dst_crs,
            resampling=Resampling.bilinear)

        # Calculate Slope using 2nd order finite difference (Horn's Method)
        # Copernicus 30m resolution ~ 30m cell size
        res = transform[0]
        x, y = np.gradient(dem_data, res)
        slope_rad = np.arctan(np.sqrt(x ** 2 + y ** 2))
        slope_deg = np.degrees(slope_rad)

        # Generate Mask and Vectorize
        mask = (slope_deg > threshold_degrees).astype('int16')

        # Extract shapes where mask is 1
        results = (
            {'properties': {'slope': threshold_degrees}, 'geometry': s}
            for i, (s, v) in enumerate(
            shapes(mask, mask=(mask == 1), transform=transform)
        )
        )

        # Save as a single dissolved polygon
        gdf = gpd.GeoDataFrame.from_features(list(results), crs=dst_crs)
        steep_slopes = gdf.dissolve()
        steep_slopes.to_file(output_vector)
        print(f"Steep slopes (> {threshold_degrees}°) saved to {output_vector}")

        # Check the EPSG (prints the code, e.g., 32629)
        print(f"Current EPSG: {steep_slopes.crs.to_epsg()}")

        # Transform to EPSG 2157 (Irish Transverse Mercator)
        steep_slopes = steep_slopes.to_crs(epsg=2157)

        # Verify the transformation
        print(f"New EPSG: {steep_slopes.crs.to_epsg()}")

        # Clip the steep slopes to the SAC boundary
        steep_slopes_in_sac = steep_slopes.clip(sac)

        # Save the clipped result
        steep_slopes_in_sac.to_file('steep_slopes_in_sac.shp')
        print("Clipped steep slopes to SAC boundary.")





