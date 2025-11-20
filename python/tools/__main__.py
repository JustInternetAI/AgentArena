"""
CLI entry point for tools.model_manager module.

This allows running the model manager as:
    python -m tools.model_manager <command> [args]
"""

from .model_manager import main

if __name__ == "__main__":
    main()
