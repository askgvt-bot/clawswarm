---
name: clawswarm
description: Spawn and manage Docker-based AI agent swarms via ClawSwarm API. Use when orchestrating multiple agents for parallel tasks, spawning research/content/coding/marketing/ops agents, or managing agent lifecycles. Requires ClawSwarm server running at localhost:8200.
---

# ClawSwarm - Agent Swarm Orchestrator

ClawSwarm spawns AI agents in Docker containers for parallel task execution.

**Base URL:** `http://localhost:8200`

## Quick Start

```bash
# Check if running
curl http://localhost:8200/health

# Quick one-shot task (spawn → run → return → kill)
curl -X POST "http://localhost:8200/quick/run?agent_type=research&task=Find%20latest%20AI%20news"

# Spawn persistent agent
curl -X POST http://localhost:8200/agents/spawn \
  -H "Content-Type: application/json" \
  -d '{"type": "coding", "name": "my-coder"}'
```

## Agent Types

| Type | Purpose |
|------|---------|
| `research` | Web research, data gathering, analysis |
| `content` | Writing, copywriting, content creation |
| `coding` | Code generation, debugging, refactoring |
| `marketing` | Campaign ideas, copy, social media |
| `ops` | DevOps tasks, system administration |
| `custom` | Generic agent with custom soul |

## API Reference

### Health & Status

```bash
GET /health              # Health check
GET /status              # Swarm status (counts + all agents)
```

### Agent Lifecycle

```bash
# Spawn agent
POST /agents/spawn
Body: {
  "type": "research|content|coding|marketing|ops|custom",
  "name": "optional-name",
  "task": "optional-initial-task",
  "soul_override": "optional-custom-prompt",
  "memory_shared": false,
  "auto_terminate": true,
  "timeout_minutes": 60
}

# List all agents
GET /agents

# Get specific agent
GET /agents/{agent_id}

# Wait for agent to be ready
GET /agents/{agent_id}/wait?timeout=30

# Kill agent
DELETE /agents/{agent_id}
```

### Task Management

```bash
# Assign task to agent
POST /agents/{agent_id}/task
Body: {
  "agent_id": "...",
  "task": "Do this thing",
  "priority": 5,
  "callback_url": "optional"
}

# Get result
GET /agents/{agent_id}/result
```

### Quick Commands

```bash
# Quick spawn by type (optionally with task)
POST /quick/spawn/{agent_type}?task=optional

# One-shot: spawn → run → get result → kill
POST /quick/run?agent_type=research&task=Find%20info%20about%20X

# Kill all agents
DELETE /quick/killall
```

## Agent Status Values

- `starting` - Container launching
- `running` - Ready and active
- `busy` - Processing a task
- `idle` - Waiting for tasks
- `stopping` - Shutting down
- `stopped` - Terminated
- `error` - Failed

## Common Patterns

### One-Shot Research Task

```bash
curl -X POST "http://localhost:8200/quick/run?agent_type=research&task=Summarize%20the%20latest%20news%20about%20OpenAI"
```

### Persistent Agent Workflow

```bash
# 1. Spawn
AGENT=$(curl -s -X POST http://localhost:8200/agents/spawn \
  -H "Content-Type: application/json" \
  -d '{"type": "coding"}' | jq -r '.id')

# 2. Wait for ready
curl "http://localhost:8200/agents/$AGENT/wait"

# 3. Assign task
curl -X POST "http://localhost:8200/agents/$AGENT/task" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\": \"$AGENT\", \"task\": \"Write a Python script to parse JSON\"}"

# 4. Poll for result
curl "http://localhost:8200/agents/$AGENT/result"

# 5. Kill when done
curl -X DELETE "http://localhost:8200/agents/$AGENT"
```

### Parallel Agent Swarm

```bash
# Spawn multiple agents
curl -X POST "http://localhost:8200/quick/spawn/research?task=Research%20competitors"
curl -X POST "http://localhost:8200/quick/spawn/content?task=Write%20blog%20post"
curl -X POST "http://localhost:8200/quick/spawn/marketing?task=Draft%20social%20campaign"

# Check swarm status
curl http://localhost:8200/status

# Cleanup
curl -X DELETE http://localhost:8200/quick/killall
```

## Troubleshooting

```bash
# Check if server running
curl http://localhost:8200/health || echo "ClawSwarm not running"

# Start server (from project dir)
cd /Users/nicholashalstead/Projects/clawswarm
uv run uvicorn src.clawswarm.main:app --host 0.0.0.0 --port 8200

# Check Docker
docker ps | grep clawswarm

# View logs
ls /Users/nicholashalstead/Projects/clawswarm/logs/
```

## Project Location

- **Repo:** `/Users/nicholashalstead/Projects/clawswarm/`
- **Docker image:** `clawswarm-agent:latest`
- **Logs:** `/Users/nicholashalstead/Projects/clawswarm/logs/`
