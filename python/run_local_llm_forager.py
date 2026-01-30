"""
Local LLM Forager Demo - Run LLM-powered agent in foraging scene.

This script demonstrates the LocalLLMBehavior integration:
1. Loads a local GGUF model via llama.cpp (or connects to vLLM server)
2. Uses GPU-accelerated inference for decision making
3. Connects to Godot foraging scene via IPC

To run:
1. Download a model: python -m tools.model_manager download tinyllama-1.1b-chat --format gguf --quant q4_k_m
2. Start this script: python run_local_llm_forager.py --model ../models/tinyllama-1.1b-chat/gguf/q4_k_m/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
3. Open Godot and load foraging.tscn
4. Press SPACE to start the simulation
"""

import argparse
import logging
import sys

from agent_runtime import AgentArena, LocalLLMBehavior
from backends import BackendConfig, LlamaCppBackend

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Default system prompt for foraging scenario
FORAGING_SYSTEM_PROMPT = """You are a foraging agent. Output ONLY valid JSON with no additional text.

Rules:
- Avoid hazards (distance < 3.0)
- Move toward resources

Output format:
{"tool": "move_to", "params": {"target_position": [x, y, z], "speed": 1.5}, "reasoning": "why"}
OR
{"tool": "idle", "params": {}, "reasoning": "why"}

Output JSON only:"""


def main():
    """Run foraging demo with LocalLLMBehavior agent."""
    parser = argparse.ArgumentParser(description="Run foraging demo with local LLM-powered agent")
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to GGUF model file",
    )
    parser.add_argument(
        "--gpu-layers",
        type=int,
        default=-1,
        help="GPU layers to offload (-1=all, 0=CPU only)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="LLM temperature (0-1)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=256,
        help="Maximum tokens per response",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="IPC server host",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="IPC server port",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        default="foraging_agent_001",
        help="Agent ID to register behavior for (must match Godot scene)",
    )
    parser.add_argument(
        "--memory-capacity",
        type=int,
        default=10,
        help="Number of recent observations to keep in memory",
    )
    parser.add_argument(
        "--system-prompt",
        type=str,
        default=None,
        help="Custom system prompt (uses default foraging prompt if not provided)",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        # Also enable debug for specific modules
        logging.getLogger("agent_runtime.local_llm_behavior").setLevel(logging.DEBUG)
        logging.getLogger("backends.llama_cpp_backend").setLevel(logging.DEBUG)
        logging.getLogger("ipc.server").setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("Local LLM Forager Demo")
    logger.info("=" * 60)
    logger.info(f"Model: {args.model}")
    gpu_desc = (
        "all"
        if args.gpu_layers == -1
        else ("CPU only" if args.gpu_layers == 0 else args.gpu_layers)
    )
    logger.info(f"GPU Layers: {args.gpu_layers} ({gpu_desc})")
    logger.info(f"Temperature: {args.temperature}")
    logger.info(f"Max Tokens: {args.max_tokens}")
    logger.info(f"Memory Capacity: {args.memory_capacity}")
    logger.info(f"Agent ID: {args.agent_id}")
    logger.info("=" * 60)

    backend = None

    try:
        # Load LLM backend
        logger.info("Loading LLM backend...")
        config = BackendConfig(
            model_path=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            n_gpu_layers=args.gpu_layers,
        )
        backend = LlamaCppBackend(config)
        logger.info("  Backend loaded successfully")

        # Determine system prompt
        system_prompt = args.system_prompt if args.system_prompt else FORAGING_SYSTEM_PROMPT

        # Create LocalLLMBehavior
        logger.info("Creating LocalLLMBehavior...")
        behavior = LocalLLMBehavior(
            backend=backend,
            system_prompt=system_prompt,
            memory_capacity=args.memory_capacity,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        logger.info("  LocalLLMBehavior created")

        # Create arena and register behavior
        logger.info("Creating AgentArena...")
        arena = AgentArena.connect(host=args.host, port=args.port, max_workers=4)

        # Register behavior for the foraging scene agent
        agent_id = args.agent_id
        arena.register(agent_id, behavior)
        logger.info(f"  Registered LocalLLMBehavior for agent_id: {agent_id}")

        registered = arena.get_registered_agents()
        logger.info(f"Total registered agents: {len(registered)}")

        # Debug: verify behaviors dict is shared with IPC server
        logger.info(f"  Arena behaviors: {list(arena.behaviors.keys())}")
        if arena.ipc_server:
            logger.info(f"  IPC server behaviors: {list(arena.ipc_server.behaviors.keys())}")
            logger.info(f"  Same dict reference: {arena.behaviors is arena.ipc_server.behaviors}")

        logger.info("")
        logger.info("=" * 60)
        logger.info("Instructions:")
        logger.info("  1. Open Godot and load scenes/foraging.tscn")
        logger.info("  2. Press F5 to run the scene")
        logger.info("  3. Press SPACE to start the simulation")
        logger.info("  4. Watch the LLM-powered agent make decisions!")
        logger.info("")
        logger.info(f"IPC Server ready at http://{args.host}:{args.port}")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        logger.info("")

        # Run the arena (blocks until stopped)
        arena.run()

    except FileNotFoundError:
        logger.error(f"Model file not found: {args.model}")
        logger.error("Download a model first:")
        logger.error(
            "  python -m tools.model_manager download tinyllama-1.1b-chat --format gguf --quant q4_k_m"
        )
        return 1
    except KeyboardInterrupt:
        logger.info("\n")
        logger.info("=" * 60)
        logger.info("Shutting down gracefully...")
        if backend is not None:
            backend.unload()
            logger.info("  Backend unloaded")
        logger.info("=" * 60)
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        if backend is not None:
            backend.unload()
        return 1


if __name__ == "__main__":
    sys.exit(main())
