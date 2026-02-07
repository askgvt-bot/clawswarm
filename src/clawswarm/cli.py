"""CLI for ClawSwarm."""

import argparse
import sys

import uvicorn


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ClawSwarm - Agent swarm orchestrator for OpenClaw"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8420,
        help="Port to bind to (default: 8420)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    args = parser.parse_args()

    print(f"""
╔═══════════════════════════════════════════════════════════╗
║                     🦞 ClawSwarm 🦞                       ║
║         Agent Swarm Orchestrator for OpenClaw             ║
╠═══════════════════════════════════════════════════════════╣
║  API:  http://{args.host}:{args.port}                          ║
║  Docs: http://{args.host}:{args.port}/docs                     ║
╚═══════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "clawswarm.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
