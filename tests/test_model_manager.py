"""
Unit tests for the Model Manager.
"""

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from tools.model_manager import ModelManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config(temp_dir):
    """Create a mock model configuration."""
    config = {
        "models": {
            "test-model": {
                "huggingface_id": "test/test-model-gguf",
                "formats": {
                    "gguf": {
                        "q4_k_m": {
                            "file": "test-model.Q4_K_M.gguf",
                            "sha256": "abc123",
                        }
                    }
                },
            }
        }
    }

    config_path = temp_dir / "models.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return config_path


@pytest.fixture
def model_manager(temp_dir, mock_config):
    """Create a ModelManager instance for testing."""
    return ModelManager(models_dir=temp_dir / "models", config_path=mock_config)


class TestModelManager:
    """Tests for ModelManager class."""

    def test_init(self, model_manager, temp_dir):
        """Test ModelManager initialization."""
        assert model_manager.models_dir == temp_dir / "models"
        assert model_manager.models_dir.exists()
        assert "models" in model_manager.registry
        assert "test-model" in model_manager.registry["models"]

    def test_get_model_dir(self, model_manager, temp_dir):
        """Test _get_model_dir method."""
        model_dir = model_manager._get_model_dir("test-model", "gguf", "q4_k_m")
        expected = temp_dir / "models" / "test-model" / "gguf" / "q4_k_m"
        assert model_dir == expected

    def test_calculate_sha256(self, model_manager, temp_dir):
        """Test SHA256 calculation."""
        test_file = temp_dir / "test.txt"
        test_content = b"Hello, World!"
        test_file.write_bytes(test_content)

        expected_hash = hashlib.sha256(test_content).hexdigest()
        actual_hash = model_manager._calculate_sha256(test_file)

        assert actual_hash == expected_hash

    def test_verify_model_file_not_found(self, model_manager, temp_dir):
        """Test verify_model with non-existent file."""
        nonexistent = temp_dir / "nonexistent.gguf"
        assert not model_manager.verify_model(nonexistent)

    def test_verify_model_no_checksum(self, model_manager, temp_dir):
        """Test verify_model without checksum (just file existence)."""
        test_file = temp_dir / "test.gguf"
        test_file.write_bytes(b"test data")

        assert model_manager.verify_model(test_file, expected_sha256=None)

    def test_verify_model_checksum_match(self, model_manager, temp_dir):
        """Test verify_model with matching checksum."""
        test_file = temp_dir / "test.gguf"
        test_content = b"test data"
        test_file.write_bytes(test_content)

        expected_hash = hashlib.sha256(test_content).hexdigest()
        assert model_manager.verify_model(test_file, expected_sha256=expected_hash)

    def test_verify_model_checksum_mismatch(self, model_manager, temp_dir):
        """Test verify_model with mismatched checksum."""
        test_file = temp_dir / "test.gguf"
        test_file.write_bytes(b"test data")

        wrong_hash = "0" * 64
        assert not model_manager.verify_model(test_file, expected_sha256=wrong_hash)

    def test_list_models_empty(self, model_manager):
        """Test list_models with no cached models."""
        models = model_manager.list_models()
        assert models == []

    def test_list_models_with_content(self, model_manager, temp_dir):
        """Test list_models with cached models."""
        # Create a fake model structure
        model_dir = temp_dir / "models" / "test-model" / "gguf" / "q4_k_m"
        model_dir.mkdir(parents=True, exist_ok=True)

        model_file = model_dir / "test-model.Q4_K_M.gguf"
        model_file.write_bytes(b"fake model data")

        models = model_manager.list_models()
        assert len(models) == 1
        assert models[0]["model"] == "test-model"
        assert models[0]["format"] == "gguf"
        assert models[0]["quantization"] == "q4_k_m"
        assert models[0]["file"] == "test-model.Q4_K_M.gguf"

    def test_list_models_with_format_filter(self, model_manager, temp_dir):
        """Test list_models with format filter."""
        # Create models with different formats
        gguf_dir = temp_dir / "models" / "test-model" / "gguf"
        gguf_dir.mkdir(parents=True, exist_ok=True)
        (gguf_dir / "model.gguf").write_bytes(b"data")

        pytorch_dir = temp_dir / "models" / "test-model" / "pytorch"
        pytorch_dir.mkdir(parents=True, exist_ok=True)
        (pytorch_dir / "model.pt").write_bytes(b"data")

        # Filter by gguf
        models = model_manager.list_models(format_filter="gguf")
        assert len(models) == 1
        assert models[0]["format"] == "gguf"

        # Filter by pytorch
        models = model_manager.list_models(format_filter="pytorch")
        assert len(models) == 1
        assert models[0]["format"] == "pytorch"

    def test_get_model_path_exists(self, model_manager, temp_dir):
        """Test get_model_path when model exists."""
        model_dir = temp_dir / "models" / "test-model" / "gguf" / "q4_k_m"
        model_dir.mkdir(parents=True, exist_ok=True)

        model_file = model_dir / "test-model.Q4_K_M.gguf"
        model_file.write_bytes(b"fake model data")

        path = model_manager.get_model_path("test-model", "gguf", "q4_k_m")
        assert path == model_file

    def test_get_model_path_not_exists(self, model_manager):
        """Test get_model_path when model doesn't exist."""
        path = model_manager.get_model_path("nonexistent", "gguf", "q4_k_m")
        assert path is None

    def test_remove_model_not_found(self, model_manager):
        """Test remove_model with non-existent model."""
        assert not model_manager.remove_model("nonexistent")

    def test_remove_model_entire_model(self, model_manager, temp_dir):
        """Test removing entire model (all formats)."""
        # Create model structure
        model_dir = temp_dir / "models" / "test-model" / "gguf" / "q4_k_m"
        model_dir.mkdir(parents=True, exist_ok=True)
        (model_dir / "model.gguf").write_bytes(b"data")

        # Remove entire model
        assert model_manager.remove_model("test-model")
        assert not (temp_dir / "models" / "test-model").exists()

    def test_remove_model_specific_format(self, model_manager, temp_dir):
        """Test removing specific format."""
        # Create multiple formats
        gguf_dir = temp_dir / "models" / "test-model" / "gguf"
        gguf_dir.mkdir(parents=True, exist_ok=True)
        (gguf_dir / "model.gguf").write_bytes(b"data")

        pytorch_dir = temp_dir / "models" / "test-model" / "pytorch"
        pytorch_dir.mkdir(parents=True, exist_ok=True)
        (pytorch_dir / "model.pt").write_bytes(b"data")

        # Remove only gguf format
        assert model_manager.remove_model("test-model", format="gguf")
        assert not gguf_dir.exists()
        assert pytorch_dir.exists()

    def test_remove_model_specific_quantization(self, model_manager, temp_dir):
        """Test removing specific quantization."""
        # Create multiple quantizations
        q4_dir = temp_dir / "models" / "test-model" / "gguf" / "q4_k_m"
        q4_dir.mkdir(parents=True, exist_ok=True)
        (q4_dir / "model.gguf").write_bytes(b"data")

        q5_dir = temp_dir / "models" / "test-model" / "gguf" / "q5_k_m"
        q5_dir.mkdir(parents=True, exist_ok=True)
        (q5_dir / "model.gguf").write_bytes(b"data")

        # Remove only q4
        assert model_manager.remove_model("test-model", format="gguf", quantization="q4_k_m")
        assert not q4_dir.exists()
        assert q5_dir.exists()

    @patch("tools.model_manager.hf_hub_download")
    def test_download_model_success(self, mock_download, model_manager, temp_dir):
        """Test successful model download."""
        # Setup mock
        model_dir = temp_dir / "models" / "test-model" / "gguf" / "q4_k_m"
        model_dir.mkdir(parents=True, exist_ok=True)
        model_file = model_dir / "test-model.Q4_K_M.gguf"

        # Create fake file content
        test_content = b"fake model content"

        # Mock download to create the file
        def mock_download_func(*args, **kwargs):
            model_file.write_bytes(test_content)
            return str(model_file)

        mock_download.side_effect = mock_download_func

        # Update config to have correct checksum
        expected_hash = hashlib.sha256(test_content).hexdigest()
        model_manager.registry["models"]["test-model"]["formats"]["gguf"]["q4_k_m"][
            "sha256"
        ] = expected_hash

        # Download model
        result = model_manager.download_model("test-model", "gguf", "q4_k_m")

        assert result == model_file
        assert model_file.exists()
        mock_download.assert_called_once()

    def test_download_model_not_in_registry(self, model_manager):
        """Test download_model with model not in registry."""
        result = model_manager.download_model("nonexistent", "gguf")
        assert result is None

    def test_download_model_format_not_available(self, model_manager):
        """Test download_model with unavailable format."""
        result = model_manager.download_model("test-model", "pytorch")
        assert result is None

    def test_download_model_quantization_not_available(self, model_manager):
        """Test download_model with unavailable quantization."""
        result = model_manager.download_model("test-model", "gguf", "q8_0")
        assert result is None

    @patch("tools.model_manager.hf_hub_download")
    def test_download_model_skip_existing(self, mock_download, model_manager, temp_dir):
        """Test that existing valid model is not re-downloaded."""
        # Create existing model
        model_dir = temp_dir / "models" / "test-model" / "gguf" / "q4_k_m"
        model_dir.mkdir(parents=True, exist_ok=True)
        model_file = model_dir / "test-model.Q4_K_M.gguf"

        test_content = b"existing model"
        model_file.write_bytes(test_content)

        # Update config with correct checksum
        expected_hash = hashlib.sha256(test_content).hexdigest()
        model_manager.registry["models"]["test-model"]["formats"]["gguf"]["q4_k_m"][
            "sha256"
        ] = expected_hash

        # Try to download (should skip)
        result = model_manager.download_model("test-model", "gguf", "q4_k_m", force=False)

        assert result == model_file
        mock_download.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
