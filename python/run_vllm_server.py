"""
Script to start a vLLM inference server.

Usage:
    python run_vllm_server.py --model meta-llama/Llama-2-7b-chat-hf
    python run_vllm_server.py --model meta-llama/Llama-2-7b-chat-hf --port 8000 --gpu-memory 0.9
"""

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Start vLLM inference server")

    # Model configuration
    parser.add_argument(
        "--model",
        type=str,
        default="meta-llama/Llama-2-7b-chat-hf",
        help="Model name or path (e.g., meta-llama/Llama-2-7b-chat-hf)",
    )

    # Server configuration
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Server host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000)",
    )

    # Performance configuration
    parser.add_argument(
        "--tensor-parallel-size",
        type=int,
        default=1,
        help="Number of GPUs to use for tensor parallelism (default: 1)",
    )
    parser.add_argument(
        "--gpu-memory",
        type=float,
        default=0.9,
        help="GPU memory utilization (0.0-1.0, default: 0.9)",
    )
    parser.add_argument(
        "--max-model-len",
        type=int,
        default=4096,
        help="Maximum model context length (default: 4096)",
    )
    parser.add_argument(
        "--dtype",
        type=str,
        default="auto",
        choices=["auto", "half", "float16", "bfloat16", "float32"],
        help="Data type for model weights (default: auto)",
    )

    # Additional options
    parser.add_argument(
        "--trust-remote-code",
        action="store_true",
        help="Trust remote code when loading model",
    )
    parser.add_argument(
        "--enable-function-calling",
        action="store_true",
        default=True,
        help="Enable function calling support (default: True)",
    )

    args = parser.parse_args()

    try:
        # Check if vLLM is installed
        try:
            import vllm

            logger.info(f"vLLM version: {vllm.__version__}")
        except ImportError:
            logger.error(
                "vLLM is not installed. Install with: pip install vllm\n"
                "Note: vLLM requires CUDA and is not available on CPU-only systems."
            )
            sys.exit(1)

        # Import vLLM server

        logger.info(f"Starting vLLM server for model: {args.model}")
        logger.info(f"Server will be available at: http://{args.host}:{args.port}")
        logger.info(f"GPU memory utilization: {args.gpu_memory}")
        logger.info(f"Tensor parallel size: {args.tensor_parallel_size}")
        logger.info(f"Max model length: {args.max_model_len}")
        logger.info(f"Data type: {args.dtype}")

        # Build command-line arguments for vLLM
        vllm_args = [
            "--model",
            args.model,
            "--host",
            args.host,
            "--port",
            str(args.port),
            "--tensor-parallel-size",
            str(args.tensor_parallel_size),
            "--gpu-memory-utilization",
            str(args.gpu_memory),
            "--max-model-len",
            str(args.max_model_len),
            "--dtype",
            args.dtype,
        ]

        if args.trust_remote_code:
            vllm_args.append("--trust-remote-code")

        if args.enable_function_calling:
            vllm_args.extend(["--enable-auto-tool-choice", "--tool-call-parser", "hermes"])

        logger.info(f"vLLM arguments: {' '.join(vllm_args)}")

        # Note: The actual server starting requires using vLLM's CLI
        # This script is a helper that shows the configuration
        logger.info("\nTo start the server, run:")
        logger.info(f"python -m vllm.entrypoints.openai.api_server {' '.join(vllm_args)}")

        # Or start directly if vLLM supports it
        import subprocess

        subprocess.run(
            ["python", "-m", "vllm.entrypoints.openai.api_server"] + vllm_args, check=True
        )

    except KeyboardInterrupt:
        logger.info("\nShutting down vLLM server...")
    except Exception as e:
        logger.error(f"Error starting vLLM server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
