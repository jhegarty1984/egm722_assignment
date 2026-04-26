# egm722_assignment
Git repository for egm722 assignment. Includes README file, .gitignore file, a LICENSE file and environment.yml file.

# SAC Habitat Suitability Analysis

## Overview
This project performs a spatial analysis of the Lough Nillan SAC. It integrates CORINE Land Cover data, Sentinel-2 satellite imagery, and Digital Elevation Models (DEM) to identify suitable peatland habitats by excluding water bodies (via NDWI) and steep slopes.

## Folder Structure
Because the spatial datasets are too large for GitHub, you must manually recreate this folder structure and place the data in the following locations:

```text
egm722_assignment/
├── egm722_assignment.py       # Main Python script
├── .gitignore                 # Prevents large data commits
└── Spatial_Data/              # (Manually create this folder)
    ├── Lough_Nillan_SAC/      # Place SAC .shp files here
    ├── Satellite_Data/
    │   ├── corine_land_cover_2018/ # Place CORINE .tif here
    │   └── Sentinel_2_Data/        # Place Sentinel-2 .SAFE folders here
    └── assignment_output_data/     # (Created automatically by script)
```

## Setup & Prerequisites
This project requires a specific Anaconda environment to handle complex geospatial drivers like OpenJPEG and GDAL.

### 1. Environment Installation
Use the following commands in your Anaconda Prompt:
```bash
conda create -n egm722_assignment python=3.11
conda activate egm722_assignment
conda install -c conda-forge geopandas rasterio shapely cartopy matplotlib-scalebar pyogrio libgdal-jp2openjpeg
```

### 2. Path Configuration
Inside `egm722_assignment.py`, you must update the `env_path` variable to match your local Anaconda installation path (e.g., `C:\Users\YOUR_NAME\anaconda3\envs\egm722_assignment`).

## Data Sources
* **Sentinel-2**: Level-2A imagery from the [Copernicus Browser](https://copernicus.eu).
* **CORINE Land Cover**: 100m raster dataset from [Copernicus Land Monitoring Service](https://copernicus.eu).
* **SAC Boundaries**: Provided by the [NPWS](https://npws.ie).

## Usage
1. Activate the environment: `conda activate egm722_assignment`
2. Run the script: `python egm722_assignment.py`
 