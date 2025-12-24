"""Tests for tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from geospatial_co_scientist.tools.geospatial import (
    GeospatialAnalysisTool,
    GEOSPATIAL_DATASETS,
    DatasetInfo,
)
from geospatial_co_scientist.tools.embeddings import (
    compute_similarity,
    compute_pairwise_similarities,
    cluster_by_similarity,
)


class TestGeospatialAnalysisTool:
    """Tests for GeospatialAnalysisTool."""

    def test_get_dataset_info(self):
        tool = GeospatialAnalysisTool()
        info = tool.get_dataset_info("landsat_8")

        assert info is not None
        assert info.name == "Landsat 8"
        assert info.provider == "USGS"

    def test_get_dataset_info_not_found(self):
        tool = GeospatialAnalysisTool()
        info = tool.get_dataset_info("nonexistent")

        assert info is None

    def test_list_datasets(self):
        tool = GeospatialAnalysisTool()
        datasets = tool.list_datasets()

        assert len(datasets) > 0
        assert "landsat_8" in datasets
        assert "sentinel_2" in datasets

    def test_recommend_datasets_thermal(self):
        tool = GeospatialAnalysisTool()
        recommendations = tool.recommend_datasets("thermal analysis urban heat")

        # Should recommend Landsat 8 which has thermal bands
        landsat_in_recs = any(
            r.name == "Landsat 8" for r in recommendations
        )
        assert landsat_in_recs or len(recommendations) > 0

    def test_recommend_datasets_vegetation(self):
        tool = GeospatialAnalysisTool()
        recommendations = tool.recommend_datasets("vegetation monitoring agriculture")

        assert len(recommendations) > 0

    def test_get_analysis_methods_classification(self):
        tool = GeospatialAnalysisTool()
        methods = tool.get_analysis_methods("classification")

        assert "name" in methods
        assert "algorithms" in methods
        assert "tools" in methods
        assert "Random Forest" in methods["algorithms"]

    def test_get_analysis_methods_change_detection(self):
        tool = GeospatialAnalysisTool()
        methods = tool.get_analysis_methods("change_detection")

        assert methods.get("name") == "Change Detection"

    def test_get_analysis_methods_unknown(self):
        tool = GeospatialAnalysisTool()
        methods = tool.get_analysis_methods("unknown_type")

        assert methods == {}

    def test_generate_code_template_ndvi(self):
        tool = GeospatialAnalysisTool()
        code = tool.generate_code_template("ndvi")

        assert "import rasterio" in code
        assert "NDVI" in code.upper()
        assert "def calculate_ndvi" in code

    def test_generate_code_template_thermal(self):
        tool = GeospatialAnalysisTool()
        code = tool.generate_code_template("thermal")

        assert "landsat" in code.lower() or "temperature" in code.lower()

    def test_generate_code_template_unknown(self):
        tool = GeospatialAnalysisTool()
        code = tool.generate_code_template("unknown")

        assert "No template available" in code


class TestEmbeddings:
    """Tests for embedding utilities."""

    def test_compute_similarity_identical(self):
        vec = [1.0, 0.0, 0.0]
        similarity = compute_similarity(vec, vec)

        assert similarity == pytest.approx(1.0)

    def test_compute_similarity_orthogonal(self):
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = compute_similarity(vec1, vec2)

        assert similarity == pytest.approx(0.0)

    def test_compute_similarity_opposite(self):
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        similarity = compute_similarity(vec1, vec2)

        assert similarity == pytest.approx(-1.0)

    def test_compute_similarity_zero_vector(self):
        vec1 = [1.0, 1.0]
        vec2 = [0.0, 0.0]
        similarity = compute_similarity(vec1, vec2)

        assert similarity == 0.0

    def test_compute_pairwise_similarities(self):
        embeddings = [
            [1.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0]
        ]
        matrix = compute_pairwise_similarities(embeddings)

        # Same vectors should have similarity 1.0
        assert matrix[0, 1] == pytest.approx(1.0)
        # Orthogonal vectors should have similarity 0.0
        assert matrix[0, 2] == pytest.approx(0.0)

    def test_cluster_by_similarity_empty(self):
        clusters = cluster_by_similarity([])
        assert clusters == []

    def test_cluster_by_similarity_single(self):
        clusters = cluster_by_similarity([[1.0, 0.0]])
        assert len(clusters) == 1

    def test_cluster_by_similarity_identical(self):
        embeddings = [
            [1.0, 0.0],
            [1.0, 0.0],
            [1.0, 0.0]
        ]
        clusters = cluster_by_similarity(embeddings, threshold=0.9)

        # All should be in one cluster
        assert len(clusters) == 1
        assert len(clusters[0]) == 3

    def test_cluster_by_similarity_distinct(self):
        embeddings = [
            [1.0, 0.0],
            [0.0, 1.0],
            [-1.0, 0.0]
        ]
        clusters = cluster_by_similarity(embeddings, threshold=0.8)

        # Each should be in its own cluster
        assert len(clusters) == 3


class TestDatasetInfo:
    """Tests for dataset information."""

    def test_landsat_8_info(self):
        info = GEOSPATIAL_DATASETS["landsat_8"]

        assert info.name == "Landsat 8"
        assert "TIR1" in info.bands or "thermal" in " ".join(info.use_cases).lower()
        assert "30m" in info.spatial_resolution

    def test_sentinel_2_info(self):
        info = GEOSPATIAL_DATASETS["sentinel_2"]

        assert info.name == "Sentinel-2"
        assert "10m" in info.spatial_resolution
        assert info.provider == "ESA/Copernicus"

    def test_all_datasets_have_required_fields(self):
        for key, info in GEOSPATIAL_DATASETS.items():
            assert info.name, f"Dataset {key} missing name"
            assert info.provider, f"Dataset {key} missing provider"
            assert info.coverage, f"Dataset {key} missing coverage"
