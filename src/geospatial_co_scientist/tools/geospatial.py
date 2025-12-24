"""Geospatial analysis tools for the Co-Scientist."""

import logging
from typing import Any, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DatasetInfo(BaseModel):
    """Information about a geospatial dataset."""

    name: str
    description: str
    provider: str
    spatial_resolution: Optional[str] = None
    temporal_resolution: Optional[str] = None
    coverage: str = "global"
    access_url: Optional[str] = None
    file_formats: list[str] = Field(default_factory=list)
    bands: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)


# Common geospatial datasets
GEOSPATIAL_DATASETS = {
    "landsat_8": DatasetInfo(
        name="Landsat 8",
        description="Landsat 8 satellite imagery with multispectral and thermal bands",
        provider="USGS",
        spatial_resolution="30m (multispectral), 100m (thermal)",
        temporal_resolution="16 days",
        coverage="global",
        access_url="https://earthexplorer.usgs.gov/",
        file_formats=["GeoTIFF"],
        bands=["Coastal", "Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2", "Pan", "Cirrus", "TIR1", "TIR2"],
        use_cases=["Land cover classification", "Urban analysis", "Water detection", "Thermal analysis"]
    ),
    "sentinel_2": DatasetInfo(
        name="Sentinel-2",
        description="High-resolution optical imagery from ESA",
        provider="ESA/Copernicus",
        spatial_resolution="10m, 20m, 60m",
        temporal_resolution="5 days",
        coverage="global",
        access_url="https://scihub.copernicus.eu/",
        file_formats=["SAFE", "GeoTIFF"],
        bands=["Coastal", "Blue", "Green", "Red", "VegRed1", "VegRed2", "VegRed3", "NIR", "NarrowNIR", "WaterVapour", "Cirrus", "SWIR1", "SWIR2"],
        use_cases=["Agriculture monitoring", "Forest monitoring", "Urban mapping", "Change detection"]
    ),
    "modis": DatasetInfo(
        name="MODIS",
        description="Moderate Resolution Imaging Spectroradiometer data",
        provider="NASA",
        spatial_resolution="250m, 500m, 1km",
        temporal_resolution="1-2 days",
        coverage="global",
        access_url="https://modis.gsfc.nasa.gov/data/",
        file_formats=["HDF", "GeoTIFF"],
        bands=["Multiple spectral bands"],
        use_cases=["Vegetation monitoring", "Fire detection", "Snow cover", "Ocean color"]
    ),
    "srtm_dem": DatasetInfo(
        name="SRTM DEM",
        description="Shuttle Radar Topography Mission Digital Elevation Model",
        provider="NASA/USGS",
        spatial_resolution="30m, 90m",
        temporal_resolution="Static",
        coverage="56°S to 60°N",
        access_url="https://earthexplorer.usgs.gov/",
        file_formats=["GeoTIFF", "HGT"],
        bands=["Elevation"],
        use_cases=["Terrain analysis", "Hydrological modeling", "Visibility analysis"]
    ),
    "gee_catalog": DatasetInfo(
        name="Google Earth Engine Data Catalog",
        description="Cloud-based access to petabytes of geospatial data",
        provider="Google",
        spatial_resolution="Varies",
        temporal_resolution="Varies",
        coverage="global",
        access_url="https://developers.google.com/earth-engine/datasets",
        file_formats=["Cloud-native"],
        bands=["Varies by dataset"],
        use_cases=["All geospatial applications", "Time series analysis", "Global studies"]
    ),
}


class GeospatialAnalysisTool:
    """Tool for geospatial analysis operations."""

    def __init__(self):
        self.datasets = GEOSPATIAL_DATASETS

    def get_dataset_info(self, dataset_key: str) -> Optional[DatasetInfo]:
        """Get information about a specific dataset."""
        return self.datasets.get(dataset_key.lower())

    def list_datasets(self) -> list[str]:
        """List available datasets."""
        return list(self.datasets.keys())

    def recommend_datasets(self, use_case: str) -> list[DatasetInfo]:
        """Recommend datasets for a use case."""
        recommendations = []
        use_case_lower = use_case.lower()

        for dataset in self.datasets.values():
            for uc in dataset.use_cases:
                if any(word in uc.lower() for word in use_case_lower.split()):
                    recommendations.append(dataset)
                    break

        return recommendations

    def get_analysis_methods(self, analysis_type: str) -> dict[str, Any]:
        """Get recommended analysis methods for a type of analysis."""
        methods = {
            "classification": {
                "name": "Land Cover Classification",
                "algorithms": [
                    "Random Forest",
                    "Support Vector Machine",
                    "Maximum Likelihood",
                    "Deep Learning (CNN)"
                ],
                "tools": ["scikit-learn", "TensorFlow", "PyTorch", "QGIS"],
                "preprocessing": [
                    "Atmospheric correction",
                    "Cloud masking",
                    "Topographic correction"
                ],
                "validation": ["Confusion matrix", "Kappa coefficient", "Overall accuracy"]
            },
            "change_detection": {
                "name": "Change Detection",
                "algorithms": [
                    "Image differencing",
                    "Post-classification comparison",
                    "Principal Component Analysis",
                    "Change Vector Analysis"
                ],
                "tools": ["ENVI", "ERDAS", "Python/rasterio"],
                "preprocessing": [
                    "Radiometric normalization",
                    "Co-registration",
                    "Atmospheric correction"
                ],
                "validation": ["Ground truth comparison", "Error matrix"]
            },
            "ndvi_analysis": {
                "name": "Vegetation Index Analysis",
                "algorithms": [
                    "NDVI calculation",
                    "EVI calculation",
                    "Time series decomposition",
                    "Phenology extraction"
                ],
                "tools": ["Google Earth Engine", "Python/rasterio", "R"],
                "formula": "NDVI = (NIR - Red) / (NIR + Red)",
                "validation": ["Field measurements", "LAI correlation"]
            },
            "thermal_analysis": {
                "name": "Thermal/Temperature Analysis",
                "algorithms": [
                    "Split-window algorithm",
                    "Single-channel method",
                    "Land Surface Temperature retrieval"
                ],
                "tools": ["Python", "ENVI", "Google Earth Engine"],
                "preprocessing": [
                    "Atmospheric correction",
                    "Emissivity correction",
                    "DN to radiance conversion"
                ],
                "validation": ["Weather station data", "In-situ measurements"]
            },
            "spatial_analysis": {
                "name": "Spatial Analysis",
                "algorithms": [
                    "Buffer analysis",
                    "Overlay operations",
                    "Spatial interpolation",
                    "Hot spot analysis"
                ],
                "tools": ["ArcGIS", "QGIS", "GeoPandas", "PostGIS"],
                "preprocessing": ["Projection alignment", "Topology checks"],
                "validation": ["Cross-validation", "Visual inspection"]
            }
        }

        return methods.get(analysis_type.lower(), {})

    def generate_code_template(
        self,
        analysis_type: str,
        dataset: str = "landsat_8"
    ) -> str:
        """Generate a code template for analysis."""
        templates = {
            "ndvi": '''
import rasterio
import numpy as np

def calculate_ndvi(nir_band_path: str, red_band_path: str) -> np.ndarray:
    """Calculate NDVI from NIR and Red bands."""
    with rasterio.open(nir_band_path) as nir_src:
        nir = nir_src.read(1).astype(float)
        profile = nir_src.profile

    with rasterio.open(red_band_path) as red_src:
        red = red_src.read(1).astype(float)

    # Avoid division by zero
    denominator = nir + red
    denominator[denominator == 0] = np.nan

    ndvi = (nir - red) / denominator

    return ndvi, profile


# Example usage for Landsat 8:
# ndvi, profile = calculate_ndvi("LC08_B5.TIF", "LC08_B4.TIF")
''',
            "classification": '''
import rasterio
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

def classify_image(
    image_path: str,
    training_samples: np.ndarray,
    training_labels: np.ndarray
) -> np.ndarray:
    """Classify a multispectral image using Random Forest."""

    with rasterio.open(image_path) as src:
        img = src.read()  # Shape: (bands, height, width)
        profile = src.profile

    # Reshape for sklearn: (pixels, bands)
    n_bands, height, width = img.shape
    img_flat = img.reshape(n_bands, -1).T

    # Train classifier
    X_train, X_test, y_train, y_test = train_test_split(
        training_samples, training_labels, test_size=0.3
    )

    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)

    # Predict
    predictions = clf.predict(img_flat)
    classified = predictions.reshape(height, width)

    return classified, profile, clf.score(X_test, y_test)
''',
            "thermal": '''
import rasterio
import numpy as np

def landsat8_lst(
    thermal_band_path: str,
    emissivity: float = 0.95
) -> np.ndarray:
    """
    Calculate Land Surface Temperature from Landsat 8 thermal band.

    Args:
        thermal_band_path: Path to Band 10 (TIR1)
        emissivity: Surface emissivity (default 0.95 for urban)

    Returns:
        LST in Celsius
    """
    # Landsat 8 Band 10 constants
    ML = 0.0003342  # Radiance multiplicative factor
    AL = 0.1        # Radiance additive factor
    K1 = 774.8853   # Thermal constant 1
    K2 = 1321.0789  # Thermal constant 2

    with rasterio.open(thermal_band_path) as src:
        dn = src.read(1).astype(float)
        profile = src.profile

    # Convert DN to radiance
    radiance = ML * dn + AL

    # Convert radiance to brightness temperature (Kelvin)
    bt = K2 / np.log((K1 / radiance) + 1)

    # Apply emissivity correction and convert to Celsius
    lst = bt / (1 + (0.00115 * bt / 1.4388) * np.log(emissivity)) - 273.15

    return lst, profile
'''
        }

        return templates.get(analysis_type.lower(), "# No template available for this analysis type")


@tool
def get_dataset_recommendations(use_case: str) -> list[dict[str, Any]]:
    """
    Get recommended geospatial datasets for a specific use case.

    Args:
        use_case: Description of the intended use (e.g., "urban heat island analysis")

    Returns:
        List of recommended datasets with details
    """
    tool = GeospatialAnalysisTool()
    recommendations = tool.recommend_datasets(use_case)
    return [r.model_dump() for r in recommendations]


@tool
def get_analysis_methodology(analysis_type: str) -> dict[str, Any]:
    """
    Get recommended methodology for a specific type of geospatial analysis.

    Args:
        analysis_type: Type of analysis (e.g., "classification", "change_detection", "ndvi_analysis")

    Returns:
        Dictionary with algorithms, tools, preprocessing steps, and validation methods
    """
    tool = GeospatialAnalysisTool()
    return tool.get_analysis_methods(analysis_type)


@tool
def generate_analysis_code(analysis_type: str) -> str:
    """
    Generate a Python code template for geospatial analysis.

    Args:
        analysis_type: Type of analysis (e.g., "ndvi", "classification", "thermal")

    Returns:
        Python code template as a string
    """
    tool = GeospatialAnalysisTool()
    return tool.generate_code_template(analysis_type)
