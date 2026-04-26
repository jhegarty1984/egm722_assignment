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
def reproject_to_itm(file_path_clc, output_path='clc_itm'):
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
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest  # Use 'bilinear' or 'cubic' for continuous data
                )
    print(f"Reprojecting {file_path_clc} to {output_name}")

#Clip CLC to SAC
def clip_clc(file_path_clc, file_path_sac, output_path= 'clc_clipped'):
    # Load the SAC vector data
    sac_df = gpd.read_file(file_path_sac)

    # Open the raster data
    with rio.open(file_path_clc) as src:
        # Ensure the vector is in the same CRS as the raster
        vector_df = vector_df.to_crs(src.crs)

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