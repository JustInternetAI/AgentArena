"""
IPC Server with Local LLM Foraging Agent.

This script starts the FastAPI server with a LocalLLMBehavior-powered agent
using GPU-accelerated llama.cpp or vLLM backend for the foraging scenario.
"""

import argparse
import logging
import sys

from agent_runtime.local_llm_behavior import create_local_llm_behavior
from agent_runtime.runtime import AgentRuntime
from backends import BackendConfig, LlamaCppBackend
from backends.vllm_backend import VLLMBackend, VLLMBackendConfig
from ipc.server import create_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Agent Arena IPC Server with Local LLM Foraging Agent"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to listen on (default: 5000)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Maximum number of concurrent agent workers (default: 4)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--backend",
        type=str,
        choices=["llama_cpp", "vllm"],
        default="llama_cpp",
        help="Backend type to use: llama_cpp or vllm (default: llama_cpp)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="../models/llama-2-7b-chat.Q4_K_M.gguf",
        help="Path to GGUF model file (for llama_cpp) or model name (for vllm)",
    )
    parser.add_argument(
        "--gpu-layers",
        type=int,
        default=-1,
        help="Number of layers to offload to GPU: -1=all, 0=CPU only (default: -1, llama_cpp only)",
    )
    parser.add_argument(
        "--vllm-api",
        type=str,
        default="http://localhost:8000/v1",
        help="vLLM API base URL (default: http://localhost:8000/v1, vllm only)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="LLM temperature for decision making (default: 0.7)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=256,
        help="Maximum tokens to generate per decision (default: 256)",
    )
    parser.add_argument(
        "--memory-capacity",
        type=int,
        default=10,
        help="Number of recent observations to keep in memory (default: 10)",
    )
    parser.add_argument(
        "--system-prompt",
        type=str,
        default=None,
        help="Custom system prompt (optional, uses default foraging prompt if not provided)",
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        default=None,
        help="Specific agent ID to assign behavior to (optional, uses default for all agents if not provided)",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        # Also enable debug for specific modules
        logging.getLogger("agent_runtime.local_llm_behavior").setLevel(logging.DEBUG)
        logging.getLogger("backends.llama_cpp_backend").setLevel(logging.DEBUG)
        logging.getLogger("ipc.server").setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("Agent Arena IPC Server - Local LLM Foraging Agent")
    logger.info("=" * 60)
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Max Workers: {args.workers}")
    logger.info(f"Backend: {args.backend}")
    logger.info(f"Model: {args.model}")
    if args.backend == "llama_cpp":
        logger.info(
            f"GPU Layers: {args.gpu_layers} ({'all' if args.gpu_layers == -1 else 'CPU only' if args.gpu_layers == 0 else args.gpu_layers})"
        )
    else:
        logger.info(f"vLLM API: {args.vllm_api}")
    logger.info(f"Temperature: {args.temperature}")
    logger.info(f"Max Tokens: {args.max_tokens}")
    logger.info(f"Memory Capacity: {args.memory_capacity}")
    if args.agent_id:
        logger.info(f"Agent ID: {args.agent_id}")
    else:
        logger.info("Agent ID: <default for all agents>")
    logger.info("=" * 60)

    backend = None

    try:
        # Create backend based on type
        if args.backend == "llama_cpp":
            backend_config = BackendConfig(
                model_path=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                n_gpu_layers=args.gpu_layers,
            )

            logger.info("Loading llama.cpp backend...")
            backend = LlamaCppBackend(backend_config)
            logger.info("✓ llama.cpp backend loaded successfully")

        elif args.backend == "vllm":
            backend_config = VLLMBackendConfig(
                model_path=args.model,
                api_base=args.vllm_api,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )

            logger.info("Connecting to vLLM server...")
            backend = VLLMBackend(backend_config)
            logger.info("✓ vLLM backend connected successfully")

        # Create LocalLLMBehavior
        logger.info("Creating LocalLLMBehavior...")
        behavior = create_local_llm_behavior(
            backend=backend,
            system_prompt=args.system_prompt,
            memory_capacity=args.memory_capacity,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        logger.info("✓ LocalLLMBehavior created successfully")

        # Create runtime
        runtime = AgentRuntime(max_workers=args.workers)

        # Create server with default behavior or specific agent behavior
        if args.agent_id:
            # Assign to specific agent ID
            behaviors = {args.agent_id: behavior}
            server = create_server(
                runtime=runtime, behaviors=behaviors, host=args.host, port=args.port
            )
            logger.info(f"✓ Behavior assigned to agent '{args.agent_id}'")
        else:
            # Use as default for all agents
            server = create_server(
                runtime=runtime, default_behavior=behavior, host=args.host, port=args.port
            )
            logger.info("✓ Behavior set as default for all agents")

        logger.info("=" * 60)
        logger.info("Server ready! You can now:")
        logger.info("  1. Open Godot and run the foraging scene")
        logger.info("  2. The agent will use the local LLM for decision making")
        logger.info("  3. Check console logs for agent reasoning")
        logger.info("")
        logger.info("Note: Make sure the Godot agent has agent_id set")
        if args.agent_id:
            logger.info(f"      (should be '{args.agent_id}')")
        else:
            logger.info("      (any agent_id will use the default behavior)")
        logger.info("=" * 60)

        # Start server
        logger.info("Starting IPC server...")
        server.run()

    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        if backend is not None:
            logger.info("Unloading LLM backend...")
            backend.unload()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        if backend is not None:
            backend.unload()
        sys.exit(1)


if __name__ == "__main__":
    main()
