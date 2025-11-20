"""
Model Download and Management Tool for Agent Arena.

This module provides functionality to download, verify, and manage LLM models
from Hugging Face Hub for use with different backends (llama.cpp, vLLM, etc.).
"""

import hashlib
import json
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml
from huggingface_hub import hf_hub_download, list_repo_files
from tqdm import tqdm

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Information about a model."""

    name: str
    huggingface_id: str
    format: str
    quantization: Optional[str] = None
    filename: Optional[str] = None
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None


class ModelManager:
    """Manages model downloads, verification, and caching."""

    def __init__(self, models_dir: Optional[Path] = None, config_path: Optional[Path] = None):
        """
        Initialize the ModelManager.

        Args:
            models_dir: Directory where models are cached. Defaults to ./models/
            config_path: Path to models.yaml config. Defaults to ./configs/models.yaml
        """
        # Find project root (directory containing configs/)
        if config_path is None:
            project_root = self._find_project_root()
            self.config_path = project_root / "configs" / "models.yaml"
        else:
            self.config_path = Path(config_path)

        if models_dir is None:
            project_root = self._find_project_root()
            self.models_dir = project_root / "models"
        else:
            self.models_dir = Path(models_dir)

        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Load model registry
        self.registry = self._load_registry()

    def _find_project_root(self) -> Path:
        """Find the project root directory by looking for configs/ directory."""
        current = Path.cwd()

        # Check current directory and parents
        for parent in [current] + list(current.parents):
            if (parent / "configs" / "models.yaml").exists():
                return parent

        # If not found, use current directory
        return current

    def _load_registry(self) -> dict[str, Any]:
        """Load the model registry from YAML config."""
        if not self.config_path.exists():
            logger.warning(f"Model registry not found at {self.config_path}")
            return {"models": {}}

        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
                return config or {"models": {}}
        except Exception as e:
            logger.error(f"Failed to load model registry: {e}")
            return {"models": {}}

    def _get_model_dir(self, model_id: str, format: str, quantization: Optional[str] = None) -> Path:
        """Get the directory path for a specific model."""
        parts = [self.models_dir, model_id, format]
        if quantization:
            parts.append(quantization)
        return Path(*parts)

    def _calculate_sha256(self, file_path: Path, chunk_size: int = 8192) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def verify_model(self, model_path: Path, expected_sha256: Optional[str] = None) -> bool:
        """
        Verify model file integrity.

        Args:
            model_path: Path to the model file
            expected_sha256: Expected SHA256 checksum (if None, just checks file exists)

        Returns:
            True if verification passes, False otherwise
        """
        if not model_path.exists():
            logger.error(f"Model file not found: {model_path}")
            return False

        if not expected_sha256:
            logger.info("No checksum provided, skipping verification")
            return True

        logger.info("Calculating checksum...")
        actual_sha256 = self._calculate_sha256(model_path)

        if actual_sha256 != expected_sha256:
            logger.error(
                f"Checksum mismatch!\nExpected: {expected_sha256}\nActual: {actual_sha256}"
            )
            return False

        logger.info("Checksum verified successfully")
        return True

    def download_model(
        self,
        model_id: str,
        format: str = "gguf",
        quantization: Optional[str] = None,
        force: bool = False,
    ) -> Optional[Path]:
        """
        Download a model from Hugging Face Hub.

        Args:
            model_id: Model identifier (e.g., "llama-2-7b-chat")
            format: Model format ("gguf", "pytorch", etc.)
            quantization: Quantization type (e.g., "q4_k_m", "q5_k_m")
            force: Force re-download even if model exists

        Returns:
            Path to the downloaded model file, or None if download failed
        """
        # Look up model in registry
        if model_id not in self.registry.get("models", {}):
            logger.error(f"Model '{model_id}' not found in registry")
            logger.info(f"Available models: {', '.join(self.registry.get('models', {}).keys())}")
            return None

        model_config = self.registry["models"][model_id]
        huggingface_id = model_config.get("huggingface_id")
        if not huggingface_id:
            logger.error(f"No huggingface_id specified for model '{model_id}'")
            return None

        # Get format-specific config
        formats = model_config.get("formats", {})
        if format not in formats:
            logger.error(f"Format '{format}' not available for model '{model_id}'")
            logger.info(f"Available formats: {', '.join(formats.keys())}")
            return None

        format_config = formats[format]

        # Get quantization-specific config
        if quantization:
            if quantization not in format_config:
                logger.error(f"Quantization '{quantization}' not available for {model_id}/{format}")
                logger.info(f"Available quantizations: {', '.join(format_config.keys())}")
                return None
            quant_config = format_config[quantization]
        else:
            # If no quantization specified, use the format config directly
            quant_config = format_config

        filename = quant_config.get("file")
        if not filename:
            logger.error(f"No filename specified for {model_id}/{format}/{quantization}")
            return None

        expected_sha256 = quant_config.get("sha256")

        # Determine download path
        model_dir = self._get_model_dir(model_id, format, quantization)
        model_path = model_dir / filename

        # Check if model already exists and is valid
        if model_path.exists() and not force:
            logger.info(f"Model already exists at {model_path}")
            if self.verify_model(model_path, expected_sha256):
                logger.info("Existing model is valid, skipping download")
                return model_path
            else:
                logger.warning("Existing model is invalid, re-downloading...")

        # Create directory
        model_dir.mkdir(parents=True, exist_ok=True)

        # Download from Hugging Face Hub
        logger.info(f"Downloading {model_id} ({format}/{quantization or 'default'})")
        logger.info(f"Source: {huggingface_id}")
        logger.info(f"File: {filename}")

        try:
            downloaded_path = hf_hub_download(
                repo_id=huggingface_id,
                filename=filename,
                local_dir=model_dir,
                local_dir_use_symlinks=False,
                resume_download=True,
            )

            # Move file to expected location if needed
            downloaded_path = Path(downloaded_path)
            if downloaded_path != model_path:
                shutil.move(str(downloaded_path), str(model_path))

            logger.info(f"Download complete: {model_path}")

            # Verify checksum
            if expected_sha256:
                if not self.verify_model(model_path, expected_sha256):
                    logger.error("Checksum verification failed!")
                    return None

            return model_path

        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None

    def list_models(self, format_filter: Optional[str] = None) -> list[dict[str, Any]]:
        """
        List all cached models.

        Args:
            format_filter: Optional filter by format (e.g., "gguf")

        Returns:
            List of model information dictionaries
        """
        cached_models = []

        if not self.models_dir.exists():
            return cached_models

        # Walk through models directory
        for model_dir in self.models_dir.iterdir():
            if not model_dir.is_dir():
                continue

            model_name = model_dir.name

            for format_dir in model_dir.iterdir():
                if not format_dir.is_dir():
                    continue

                format_name = format_dir.name

                if format_filter and format_name != format_filter:
                    continue

                # Check for quantization subdirectories
                for item in format_dir.iterdir():
                    if item.is_dir():
                        # Quantization directory
                        quant_name = item.name
                        for model_file in item.iterdir():
                            if model_file.is_file():
                                size_bytes = model_file.stat().st_size
                                cached_models.append(
                                    {
                                        "model": model_name,
                                        "format": format_name,
                                        "quantization": quant_name,
                                        "file": model_file.name,
                                        "path": str(model_file),
                                        "size_bytes": size_bytes,
                                        "size_gb": size_bytes / (1024**3),
                                    }
                                )
                    elif item.is_file():
                        # Model file directly in format directory
                        size_bytes = item.stat().st_size
                        cached_models.append(
                            {
                                "model": model_name,
                                "format": format_name,
                                "quantization": None,
                                "file": item.name,
                                "path": str(item),
                                "size_bytes": size_bytes,
                                "size_gb": size_bytes / (1024**3),
                            }
                        )

        return cached_models

    def get_model_path(
        self, model_id: str, format: str = "gguf", quantization: Optional[str] = None
    ) -> Optional[Path]:
        """
        Get the local path to a cached model.

        Args:
            model_id: Model identifier
            format: Model format
            quantization: Quantization type (optional)

        Returns:
            Path to the model file if it exists, None otherwise
        """
        model_dir = self._get_model_dir(model_id, format, quantization)

        if not model_dir.exists():
            return None

        # Find the first model file in the directory
        for item in model_dir.iterdir():
            if item.is_file() and not item.name.startswith("."):
                return item

        return None

    def remove_model(
        self, model_id: str, format: Optional[str] = None, quantization: Optional[str] = None
    ) -> bool:
        """
        Remove a cached model.

        Args:
            model_id: Model identifier
            format: Model format (if None, removes all formats)
            quantization: Quantization type (if None, removes all quantizations)

        Returns:
            True if model was removed, False otherwise
        """
        model_base_dir = self.models_dir / model_id

        if not model_base_dir.exists():
            logger.warning(f"Model '{model_id}' not found in cache")
            return False

        if format is None:
            # Remove entire model directory
            shutil.rmtree(model_base_dir)
            logger.info(f"Removed all versions of model '{model_id}'")
            return True

        format_dir = model_base_dir / format

        if not format_dir.exists():
            logger.warning(f"Format '{format}' not found for model '{model_id}'")
            return False

        if quantization is None:
            # Remove entire format directory
            shutil.rmtree(format_dir)
            logger.info(f"Removed {model_id}/{format}")

            # Clean up empty model directory
            if not any(model_base_dir.iterdir()):
                model_base_dir.rmdir()

            return True

        quant_dir = format_dir / quantization

        if not quant_dir.exists():
            logger.warning(
                f"Quantization '{quantization}' not found for {model_id}/{format}"
            )
            return False

        # Remove quantization directory
        shutil.rmtree(quant_dir)
        logger.info(f"Removed {model_id}/{format}/{quantization}")

        # Clean up empty directories
        if not any(format_dir.iterdir()):
            format_dir.rmdir()
        if not any(model_base_dir.iterdir()):
            model_base_dir.rmdir()

        return True


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Model Download and Management Tool for Agent Arena"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Download command
    download_parser = subparsers.add_parser("download", help="Download a model")
    download_parser.add_argument("model_id", help="Model identifier")
    download_parser.add_argument(
        "--format", default="gguf", help="Model format (default: gguf)"
    )
    download_parser.add_argument(
        "--quant", "--quantization", dest="quantization", help="Quantization type (e.g., q4_k_m)"
    )
    download_parser.add_argument(
        "--force", action="store_true", help="Force re-download even if model exists"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List cached models")
    list_parser.add_argument("--format", help="Filter by format")

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify a model")
    verify_parser.add_argument("model_id", help="Model identifier")
    verify_parser.add_argument("--format", default="gguf", help="Model format")
    verify_parser.add_argument("--quant", dest="quantization", help="Quantization type")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a cached model")
    remove_parser.add_argument("model_id", help="Model identifier")
    remove_parser.add_argument("--format", help="Model format")
    remove_parser.add_argument("--quant", dest="quantization", help="Quantization type")

    # Info command
    info_parser = subparsers.add_parser("info", help="Show information about available models")
    info_parser.add_argument("model_id", nargs="?", help="Specific model to show info for")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    manager = ModelManager()

    if args.command == "download":
        model_path = manager.download_model(
            args.model_id,
            format=args.format,
            quantization=args.quantization,
            force=args.force,
        )
        if model_path:
            print(f"\n[SUCCESS] Model downloaded successfully!")
            print(f"Path: {model_path}")
        else:
            print("\n[FAILED] Download failed")
            exit(1)

    elif args.command == "list":
        models = manager.list_models(format_filter=args.format)

        if not models:
            print("No cached models found")
            return

        print("\nCached Models:")
        print("=" * 80)

        total_size = 0
        for model in models:
            quant = f"/{model['quantization']}" if model["quantization"] else ""
            size_gb = model["size_gb"]
            total_size += model["size_bytes"]

            print(f"{model['model']:<25} {model['format']:<10}{quant:<15} {size_gb:>6.2f} GB")

        print("=" * 80)
        print(f"Total storage: {total_size / (1024**3):.2f} GB")

    elif args.command == "verify":
        model_path = manager.get_model_path(
            args.model_id, format=args.format, quantization=args.quantization
        )

        if not model_path:
            print(f"[FAILED] Model not found: {args.model_id}")
            exit(1)

        # Get expected SHA256 from registry
        expected_sha256 = None
        if args.model_id in manager.registry.get("models", {}):
            model_config = manager.registry["models"][args.model_id]
            formats = model_config.get("formats", {})
            if args.format in formats:
                format_config = formats[args.format]
                if args.quantization and args.quantization in format_config:
                    expected_sha256 = format_config[args.quantization].get("sha256")
                else:
                    expected_sha256 = format_config.get("sha256")

        if manager.verify_model(model_path, expected_sha256):
            print(f"[SUCCESS] Model verified successfully: {model_path}")
        else:
            print(f"[FAILED] Verification failed: {model_path}")
            exit(1)

    elif args.command == "remove":
        if manager.remove_model(args.model_id, format=args.format, quantization=args.quantization):
            print(f"[SUCCESS] Model removed successfully")
        else:
            print(f"[FAILED] Failed to remove model")
            exit(1)

    elif args.command == "info":
        if args.model_id:
            # Show info for specific model
            if args.model_id not in manager.registry.get("models", {}):
                print(f"Model '{args.model_id}' not found in registry")
                exit(1)

            model_config = manager.registry["models"][args.model_id]
            print(f"\nModel: {args.model_id}")
            print(f"Hugging Face ID: {model_config.get('huggingface_id')}")
            print("\nAvailable formats:")
            for fmt, fmt_config in model_config.get("formats", {}).items():
                print(f"  {fmt}:")
                if isinstance(fmt_config, dict):
                    for quant, quant_config in fmt_config.items():
                        if isinstance(quant_config, dict):
                            print(f"    {quant}: {quant_config.get('file', 'N/A')}")
        else:
            # List all available models
            print("\nAvailable models in registry:")
            print("=" * 80)
            for model_id in manager.registry.get("models", {}).keys():
                model_config = manager.registry["models"][model_id]
                hf_id = model_config.get("huggingface_id", "N/A")
                formats = ", ".join(model_config.get("formats", {}).keys())
                print(f"{model_id:<25} {hf_id:<40} [{formats}]")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
