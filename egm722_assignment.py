import os

# Define Project Database
os.environ['PROJ_LIB'] = r'C:\Users\hegar\anaconda3\envs\egm722_assignment\Library\share\proj'

# Direct Python to the correct GDAL plugins in your Anaconda environment
env_path = r'C:\Users\hegar\anaconda3\envs\egm722_assignment'
os.environ['GDAL_DRIVER_PATH'] = os.path.join(env_path, r'Library\lib\gdalplugins')
os.environ['GDAL_DATA'] = os.path.join(env_path, r'Library\share\gdal')
os.environ['PROJ_LIB'] = os.path.join(env_path, r'Library\share\proj')

from rasterio import crs
import shapely
import pandas as pd
import geopandas as gpd
import numpy as np
import rasterio as rio
import cartopy.crs as ccrs
import matplotlib.pyplot as plt

from rasterio.features import shapes
from shapely.geometry import shape
from rasterio._warp import Resampling
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform
from rasterio.warp import reproject

from pathlib import Path
from matplotlib_scalebar.scalebar import ScaleBar
from matplotlib.lines import Line2D


# Define the full file path to the Lough Nillan SAC shapefile
file_path_sac = r'C:\Users\hegar\egm722_assignment\Spatial_Data\Lough_Nillan_SAC\lough_nillan_sac.shp'

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
file_path_clc = r'C:\Users\hegar\egm722_assignment\Spatial_Data\Satellite_Data\corine_land_cover_2018\64554\Results\u2018_clc2018_v2020_20u1_raster100m\u2018_clc2018_v2020_20u1_raster100m\DATA\U2018_CLC2018_V2020_20u1.tif'

# Open the CLC dataset
with rio.open(file_path_clc) as src:
    # Read the data (band 1) as a NumPy array
    clc_data = src.read(1)

    # Access metadata important for clc (CRS is usually EPSG:3035)
    print(src.crs)

#Reproject CLC to ITM (CRS 2157)
def reproject_to_itm(file_path_clc, output_path = 'clc_itm', clc_itm = r'C:\Users\hegar\egm722_assignment\Spatial_Data\assignment_output_data\clc_itm.tif'):
    dst_crs = ccrs.CRS.from_string('EPSG:2157')

    with rio.open(file_path_clc) as src:
        # Calculate the transform and dimensions for the new CRS
        transform, width, height = calculate_default_transform(
            src.crs,
            dst_crs,
            src.height,
            src.width,
            *src.bounds
        )

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
def clip_clc(file_path_clc, file_path_sac, output_path = 'clc_clipped', clc_clipped = r'C:\Users\hegar\egm722_assignment\Spatial_Data\assignment_output_data\clc_clipped.tif'):

    # Load the SAC vector data
    sac_df = gpd.read_file(file_path_sac)

    # Open the raster data
    with rio.open(clc_clipped) as src:
        # Ensure the vector is in the same CRS as the raster
        sac_df = sac_df.to_crs(src.crs)

        # Get the geometry from the vector (mask expects a list of shapes)
        shapes = sac_df.geometry.values

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
def extract_habitats(clc_clipped, output_vector_path = 'peatland_habitats', peatland_habitats = r'C:\Users\hegar\egm722_assignment\Spatial_Data\assignment_output_data\peatland_habitats.shp'):
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
        output_vector_path = Path(peatland_habitats)
        gdf.to_file(output_vector_path)
        print(f" Habitats saved to {output_vector_path}")

# Define the full file path to the Sentinel-2 raster data
# Define the path to the specific band files (.jp2)
base_path_sen2 = r'C:\Users\hegar\egm722_assignment\Spatial_Data\Satellite_Data\Sentinel_2_Data\S2A_MSIL2A_20250521.SAFE\S2A_MSIL2A_20250521.SAFE\GRANULE\L2A_T29UNA_A051772_20250521T114403\IMG_DATA\R10m'

# Specific band (Red, Green, Blue & NIR) file names
blue_path = os.path.join(base_path_sen2, r'C:\Users\hegar\egm722_assignment\Spatial_Data\Satellite_Data\Sentinel_2_Data\S2A_MSIL2A_20250521.SAFE\S2A_MSIL2A_20250521.SAFE\GRANULE\L2A_T29UNA_A051772_20250521T114403\IMG_DATA\R10m\T29UNA_20250521T114401_B02_10m.jp2')
green_path = os.path.join(base_path_sen2, r'CC:\Users\hegar\egm722_assignment\Spatial_Data\Satellite_Data\Sentinel_2_Data\S2A_MSIL2A_20250521.SAFE\S2A_MSIL2A_20250521.SAFE\GRANULE\L2A_T29UNA_A051772_20250521T114403\IMG_DATA\R10m\T29UNA_20250521T114401_B03_10m.jp2')
red_path = os.path.join(base_path_sen2, r'C:\Users\hegar\egm722_assignment\Spatial_Data\Satellite_Data\Sentinel_2_Data\S2A_MSIL2A_20250521.SAFE\S2A_MSIL2A_20250521.SAFE\GRANULE\L2A_T29UNA_A051772_20250521T114403\IMG_DATA\R10m\T29UNA_20250521T114401_B04_10m.jp2')
nearir_path = os.path.join(base_path_sen2, r'C:\Users\hegar\egm722_assignment\Spatial_Data\Satellite_Data\Sentinel_2_Data\S2A_MSIL2A_20250521.SAFE\S2A_MSIL2A_20250521.SAFE\GRANULE\L2A_T29UNA_A051772_20250521T114403\IMG_DATA\R10m\T29UNA_20250521T114401_B08_10m.jp2')

# Calculate NDWI from Sentinel-2 raster data & create vector polygon of surface water bodies
def calculate_ndwi(green_path, nearir_path, output_path = 'ndwi_water_bodies', ndwi_water_bodies = r'C:\Users\hegar\egm722_assignment\Spatial_Data\assignment_output_data\ndwi_water_bodies.shp', threshold = 0.2):
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

        # Convert to GeoDataFrame and dissolve into a single polygon
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
        output_path = Path(ndwi_water_bodies)
        ndwi_water_polygon.to_file(output_path)
        print(f"Surface water polygon saved to {output_path}")

        # Save the clipped result
        output_filename = "water_in_sac.shp"
        clipped_water_path = Path(output_filename)
        water_in_sac.to_file(clipped_water_path)
        print("Clipped water bodies to SAC boundary.")



# Define the full file path to DEM raster data
dem_path = r'C:\Users\hegar\egm722_assignment\Spatial_Data\Satellite_Data\corine_land_cover_2018\64554\Results\u2018_clc2018_v2020_20u1_raster100m\u2018_clc2018_v2020_20u1_raster100m\DATA\U2018_CLC2018_V2020_20u1.tif'

def extract_slopes_to_shp(dem_path, output_shp = 'steep_slopes', steep_slopes = r'C:\Users\hegar\egm722_assignment\Spatial_Data\assignment_output_data\steep_slopes.shp', threshold=30):
    with rio.open(dem_path) as src:
        res = src.res[0]  # Assuming square pixels
        meta = src.meta
        all_features = []

        # Process in chunks (e.g., 2048x2048 pixels) to save RAM
        for ji, window in src.block_windows(1):
            # Read chunk with 1-pixel buffer for gradient calculation at edges
            padded_window = src.window_pad(window, pad_width=1)
            data = src.read(1, window=padded_window, boundless=True, fill_value=0)

            # Calculate Slope (in degrees)
            dx, dy = np.gradient(data, res)
            slope = np.arctan(np.sqrt(dx ** 2 + dy ** 2)) * (180 / np.pi)

            # Crop padding back to original window size
            row_start = 1 if padded_window.row_off < window.row_off else 0
            col_start = 1 if padded_window.col_off < window.col_off else 0
            slope_chunk = slope[row_start:row_start + window.height, col_start:col_start + window.width]

            # Create a binary mask of steep slopes (1 = steep, 0 = flat)
            steep_mask = (slope_chunk > threshold).astype(np.int16)

            # Vectorize ONLY the steep areas (where value is 1)
            # transform=src.window_transform(window) ensures shapes are in real-world coords
            chunk_shapes = shapes(
                steep_mask,
                mask=(steep_mask == 1),
                transform=src.window_transform(window)
            )

            # Convert to Shapely geometries and store
            for geom, val in chunk_shapes:
                all_features.append({'geometry': shape(geom), 'slope_val': val})

        # Save to Shapefile
        if all_features:
            gdf = gpd.GeoDataFrame(all_features, crs=src.crs)
            # Re-project to ITM (EPSG:2157) as per your original code
            gdf = gdf.to_crs(epsg=2157)
            output_shp = Path(steep_slopes)
            gdf.to_file(output_shp)
            print(f"Success! Saved steep slopes to {output_shp}")
        else:
            print("No slopes found above the threshold.")

#Refining Peatland Survey Area
def refine_peatland_habitats(output_vector_path, clipped_water_path, output_shp, output_refined_path = 'refined_survey_area', refined_survey_area = r'C:\Users\hegar\egm722_assignment\Spatial_Data\assignment_output_data\refined_survey_area.shp'):
    """
    Excludes surface water and steep slopes from the peatland habitats layer.
    """
    # Load the vector layers
    peatland = gpd.read_file(output_vector_path)
    water = gpd.read_file(clipped_water_path)
    slopes = gpd.read_file(output_shp)

    # Ensure all layers are in the same CRS (ITM EPSG:2157)
    target_crs = peatland.crs
    if water.crs != target_crs:
        water = water.to_crs(target_crs)
    if slopes.crs != target_crs:
        slopes = slopes.to_crs(target_crs)

    # Combine water and slopes into one exclusion mask
    # Use pd.concat and then dissolve to speed up the overlay process
    exclusion_zones = gpd.GeoDataFrame(
        pd.concat([water, slopes], ignore_index=True),
        crs=target_crs
    )

    # Perform the 'Difference' overlay. This keeps only the parts of 'peatland' that DO NOT overlap with 'exclusion_zones'
    print("Performing spatial subtraction (this may take a moment)...")
    refined_gdf = gpd.overlay(peatland, exclusion_zones, how='difference')

    # Clean up the result (remove tiny sliver polygons < 1m2)
    refined_gdf = refined_gdf[refined_gdf.geometry.area > 1]

    # Save the final output
    refined_gdf.to_file(Path(output_refined_path))
    print(f"Refined peatland habitats saved to: {output_refined_path}")

    return refined_gdf

#Generate Map
def generate_map(refined_gdf, sac_gdf, output_map = r'C:\Users\hegar\egm722_assignment\Spatial_Data\assignment_output_data\output_map.pdf'):
    # Setup the figure and axis with the ITM projection (EPSG:2157)
    # Use ccrs.TransverseMercator for ITM-like plotting in Cartopy
    itm_proj = ccrs.TransverseMercator(central_longitude=-8.0, central_latitude=53.5,
                                       false_easting=600000, false_northing=750000,
                                       scale_factor=1.000035)

    fig, ax = plt.subplots(figsize=(12, 10), subplot_kw={'projection': itm_proj})

    # Plot the Refined Peatland Habitats
    # Use a dictionary to map habitat types to colors
    color_map = {"Peat Bog": "darkgreen", "Heathland": "lightgreen"}

    for habitat_type, color in color_map.items():
        subset = refined_gdf[refined_gdf['habitat'] == habitat_type]
        if not subset.empty:
            subset.plot(ax=ax, color=color, label=habitat_type, edgecolor='none')

    # Plot the SAC boundary (Transparent fill, thick red outline)
    sac_gdf.plot(ax=ax, facecolor='none', edgecolor='red', linewidth=2.5, label='SAC Boundary')

    # Set map extent (Center on SAC and show entire area)
    bounds = sac_gdf.total_bounds  # [minx, miny, maxx, maxy]
    ax.set_extent([bounds[0] - 1000, bounds[2] + 1000, bounds[1] - 1000, bounds[3] + 1000], crs=itm_proj)

    # Add Legend
    legend_elements = [
        Line2D([0], [0], color='darkgreen', lw=4, label='Peat Bog'),
        Line2D([0], [0], color='lightgreen', lw=4, label='Heathland'),
        Line2D([0], [0], color='red', lw=2, label='SAC Boundary')
    ]
    ax.legend(handles=legend_elements, loc='lower right', title="Legend")

    # Add Scalebar. Since data is in ITM (meters), dx=1
    scalebar = ScaleBar(dx=1, units="m", location="lower left", length_fraction=0.2)
    ax.add_artist(scalebar)

    # Add North Arrow (Top Right)
    x, y, arrow_length = 0.95, 0.95, 0.05
    ax.annotate('N', xy=(x, y), xytext=(x, y - arrow_length),
                arrowprops=dict(facecolor='black', width=5, headwidth=15),
                ha='center', va='center', fontsize=20, xycoords='axes fraction')

    # Title and Formatting
    plt.title("Refined Habitat Survey Area: Lough Nillan SAC", fontsize=16, pad=20)

    # Save the map
    plt.savefig(output_map, dpi=300, bbox_inches='tight')
    plt.show()




