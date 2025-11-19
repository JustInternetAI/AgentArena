"""
IPC Server with GPU-accelerated agent backend.

This script starts the FastAPI server with LLM-powered agents using
GPU-accelerated llama.cpp backend.
"""

import argparse
import logging
import sys

from agent_runtime.runtime import AgentRuntime
from agent_runtime.agent import Agent
from agent_runtime.tool_dispatcher import ToolDispatcher
from backends import LlamaCppBackend, BackendConfig
from ipc.server import create_server
from tools import register_movement_tools, register_inventory_tools, register_world_query_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Agent Arena IPC Server with GPU-Accelerated LLM Backend"
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
        "--model",
        type=str,
        default="../models/llama-2-7b-chat.Q4_K_M.gguf",
        help="Path to GGUF model file (default: ../models/llama-2-7b-chat.Q4_K_M.gguf)"
    )
    parser.add_argument(
        "--gpu-layers",
        type=int,
        default=-1,
        help="Number of layers to offload to GPU: -1=all, 0=CPU only (default: -1)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="LLM temperature for decision making (default: 0.7)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=256,
        help="Maximum tokens to generate per decision (default: 256)"
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("Agent Arena IPC Server (GPU-Accelerated)")
    logger.info("=" * 60)
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Max Workers: {args.workers}")
    logger.info(f"Model: {args.model}")
    logger.info(f"GPU Layers: {args.gpu_layers} ({'all' if args.gpu_layers == -1 else 'CPU only' if args.gpu_layers == 0 else args.gpu_layers})")
    logger.info(f"Temperature: {args.temperature}")
    logger.info(f"Max Tokens: {args.max_tokens}")
    logger.info("=" * 60)

    try:
        # Create GPU-accelerated backend configuration
        backend_config = BackendConfig(
            model_path=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            n_gpu_layers=args.gpu_layers
        )

        logger.info("Loading GPU-accelerated LLM backend...")
        backend = LlamaCppBackend(backend_config)
        logger.info("✓ Backend loaded successfully")

        # Create runtime
        runtime = AgentRuntime(max_workers=args.workers)

        # Create tool dispatcher and register all tools
        tool_dispatcher = ToolDispatcher()
        register_movement_tools(tool_dispatcher)
        register_inventory_tools(tool_dispatcher)
        register_world_query_tools(tool_dispatcher)
        logger.info(f"✓ Registered {len(tool_dispatcher.tools)} tools")

        # Create a test agent with GPU backend
        test_agent = Agent(
            agent_id="gpu_agent_001",
            backend=backend,
            tools=list(tool_dispatcher.tools.keys()),
            goals=["explore the world", "collect resources", "survive"]
        )

        runtime.register_agent(test_agent)
        logger.info(f"✓ Registered agent '{test_agent.state.agent_id}' with GPU backend and {len(test_agent.available_tools)} tools")

        logger.info("=" * 60)
        logger.info("Server ready! You can now:")
        logger.info("  1. Run Godot test scenes")
        logger.info("  2. Send POST requests to /tick with agent observations")
        logger.info("  3. Execute tools via POST /tools/execute")
        logger.info("=" * 60)

        # Create and start server
        server = create_server(runtime=runtime, host=args.host, port=args.port)
        logger.info("Starting IPC server...")
        server.run()

    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        if 'backend' in locals():
            logger.info("Unloading LLM backend...")
            backend.unload()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        if 'backend' in locals():
            backend.unload()
        sys.exit(1)


if __name__ == "__main__":
    main()
