# this allows figures to be shown, but not interactively
%matplotlib inline

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
sac.crs

# Generate the minimum rotated rectangle that covers the sac
sac_area = sac.minimum_rotated_rectangle

# a sign of 1 means oriented counter-clockwise
sac_area = shapely.geometry.polygon.orient(sac_area, sign=1)

# Define the full file path to the Corrine Landcover raster data
file_path_clc = r'C:\GIS_MSc\2026\EGM722_Programming_for_GIS&Remote_Sensing\Assignment\Spatial_Data\Satellite_Data\corine_land_cover_2018\64554\Results\u2018_clc2018_v2020_20u1_raster100m\u2018_clc2018_v2020_20u1_raster100m\DATA\U2018_CLC2018_V2020_20u1.tif'

# Open the clc dataset
with rasterio.open(file_path_clc) as src:
    # Read the data (band 1) as a NumPy array
    clc_data = src.read(1)

    # Access metadata important for clc (CRS is usually EPSG:3035)
    print(f"Coordinate Reference System: {src.crs}")
    print(f"Data Type: {src.dtypes[0]}")