# 🦞 ClawSwarm

Agent swarm orchestrator for OpenClaw. Spin up/down AI agents on demand.

## Overview

ClawSwarm lets you manage a fleet of specialized AI agents running in Docker containers. Each agent has its own personality (SOUL.md), memory, and specialization.

```
┌─────────────────────────────────────────┐
│            ClawSwarm (API)              │
│  ┌─────────────────────────────────┐    │
│  │  POST /agents/spawn             │    │
│  │  GET  /status                   │    │
│  │  POST /agents/{id}/task         │    │
│  │  DELETE /agents/{id}            │    │
│  └─────────────────────────────────┘    │
│                  │                      │
│    ┌─────────────┼─────────────┐        │
│    ▼             ▼             ▼        │
│ ┌──────┐    ┌──────┐    ┌──────┐        │
│ │Market│    │Resrch│    │ Ops  │        │
│ │Agent │    │Agent │    │Agent │        │
│ └──────┘    └──────┘    └──────┘        │
└─────────────────────────────────────────┘
```

## Agent Types

| Type | Specialty |
|------|-----------|
| `marketing` | Copy, social media, growth |
| `research` | Web research, analysis, citations |
| `content` | Blog posts, docs, landing pages |
| `ops` | DevOps, deployments, monitoring |
| `coding` | Software engineering, code review |
| `custom` | Bring your own SOUL.md |

## Quick Start

```bash
# Install
cd clawswarm
pip install -e .

# Start the orchestrator
clawswarm --port 8420

# Or with auto-reload for dev
clawswarm --reload
```

## API Usage

```bash
# Check swarm status
curl http://localhost:8420/status

# Spawn a marketing agent
curl -X POST http://localhost:8420/agents/spawn \
  -H "Content-Type: application/json" \
  -d '{"type": "marketing", "task": "Write launch tweets for PromptHub"}'

# List all agents
curl http://localhost:8420/agents

# Assign a task
curl -X POST http://localhost:8420/agents/{agent_id}/task \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "abc123", "task": "Write a blog post about AI prompt management"}'

# Get result
curl http://localhost:8420/agents/{agent_id}/result

# Kill an agent
curl -X DELETE http://localhost:8420/agents/{agent_id}

# Kill all agents
curl -X DELETE http://localhost:8420/quick/killall
```

## MCP Integration

ClawSwarm exposes MCP tools for AI-to-AI communication:

- `swarm_status` - Get swarm status
- `swarm_spawn` - Spawn a new agent
- `swarm_list` - List all agents
- `swarm_assign` - Assign task to agent
- `swarm_result` - Get task result
- `swarm_kill` - Kill an agent
- `swarm_scale` - Spawn multiple agents

## Docker

Each agent runs in its own Docker container with:
- 2GB memory limit
- 1 CPU limit
- Isolated networking
- Custom SOUL.md personality

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with reload
clawswarm --reload
```

## License

MIT
