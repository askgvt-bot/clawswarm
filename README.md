# 🦞 ClawSwarm

**Agent swarm orchestrator for OpenClaw** — Spin up and coordinate multiple AI agents running in Docker containers.

ClawSwarm lets you spawn specialized AI agents (research, coding, content, ops) and coordinate them on complex tasks. Each agent runs in its own Docker container with OpenClaw, enabling true parallel AI workloads.

## Features

- 🐳 **Dockerized Agents** — Each agent runs in isolation with its own OpenClaw instance
- 🎯 **Specialized Types** — Research, Content, Coding, and Ops agent templates
- 🔄 **Task Coordination** — Assign tasks and collect results via REST API
- 📊 **Status Dashboard** — Monitor all agents in real-time
- 🔌 **MCP Compatible** — Use as an MCP server for tool integration
- ⚡ **Parallel Execution** — Run multiple agents simultaneously

## Quick Start

### Prerequisites

- Docker
- Python 3.11+
- OpenAI API key (or Anthropic)

### Installation

```bash
git clone https://github.com/askgvt-bot/clawswarm.git
cd clawswarm

# Install dependencies
pip install -e .

# Build the agent Docker image
cd docker-agent
docker build -t clawswarm-agent:latest .
cd ..

# Set your API key
export OPENAI_API_KEY="sk-..."

# Start the orchestrator
uvicorn src.clawswarm.api:app --host 0.0.0.0 --port 8200
```

### Spawn Your First Agent

```bash
# Spawn a research agent
curl -X POST http://localhost:8200/agents/spawn \
  -H "Content-Type: application/json" \
  -d '{"type": "research", "name": "researcher"}'

# Check status
curl http://localhost:8200/status

# Send a task
curl -X POST http://localhost:8500/task \
  -H "Content-Type: application/json" \
  -d '{"task": "Research the top 3 AI trends in 2025"}'

# Get result
curl http://localhost:8500/result
```

## API Reference

### Orchestrator API (port 8200)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Swarm status with all agents |
| `/agents/spawn` | POST | Spawn a new agent |
| `/agents` | GET | List all agents |
| `/agents/{id}` | GET | Get agent details |
| `/agents/{id}` | DELETE | Kill an agent |

### Agent API (ports 8500+)

Each spawned agent exposes its own API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Agent health and status |
| `/task` | POST | Assign a task (`{"task": "..."}`) |
| `/result` | GET | Get task result |
| `/status` | GET | Detailed agent status |

## Agent Types

| Type | Icon | Specialty |
|------|------|-----------|
| `research` | 🔬 | Web research, analysis, documentation |
| `content` | ✍️ | Writing, editing, content creation |
| `coding` | 💻 | Code generation, reviews, debugging |
| `ops` | ⚙️ | DevOps, infrastructure, deployment |
| `custom` | 🤖 | Custom soul/personality |

### Custom Agent Soul

You can provide a custom SOUL.md for any agent:

```bash
curl -X POST http://localhost:8200/agents/spawn \
  -H "Content-Type: application/json" \
  -d '{
    "type": "custom",
    "name": "my-agent",
    "soul_override": "# My Agent\n\nYou are a specialized assistant for..."
  }'
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ClawSwarm Orchestrator                │
│                      (port 8200)                         │
├─────────────────────────────────────────────────────────┤
│  POST /agents/spawn  │  GET /status  │  GET /agents     │
└──────────┬───────────┴───────┬───────┴────────┬─────────┘
           │                   │                │
     ┌─────▼─────┐       ┌─────▼─────┐    ┌─────▼─────┐
     │  Agent 1  │       │  Agent 2  │    │  Agent N  │
     │  Docker   │       │  Docker   │    │  Docker   │
     │  :8500    │       │  :8501    │    │  :850N    │
     └───────────┘       └───────────┘    └───────────┘
           │                   │                │
     ┌─────▼─────┐       ┌─────▼─────┐    ┌─────▼─────┐
     │ OpenClaw  │       │ OpenClaw  │    │ OpenClaw  │
     │  Agent    │       │  Agent    │    │  Agent    │
     └───────────┘       └───────────┘    └───────────┘
```

## Coordinated Tasks Example

Run multiple agents in parallel and combine their outputs:

```python
import httpx
import asyncio

ORCHESTRATOR = "http://localhost:8200"

async def coordinated_task():
    async with httpx.AsyncClient() as client:
        # Spawn agents
        agents = []
        for agent_type in ["research", "coding", "content"]:
            r = await client.post(f"{ORCHESTRATOR}/agents/spawn", 
                json={"type": agent_type, "name": agent_type})
            agents.append(r.json())
        
        await asyncio.sleep(5)  # Wait for containers to start
        
        # Assign tasks in parallel
        tasks = [
            ("research", "Find 3 Python web frameworks and their pros/cons"),
            ("coding", "Write a hello world FastAPI app"),
            ("content", "Write a tweet about Python web development"),
        ]
        
        for (agent_type, task) in tasks:
            port = 8500 + ["research", "coding", "content"].index(agent_type)
            await client.post(f"http://localhost:{port}/task", 
                json={"task": task})
        
        # Wait and collect results
        await asyncio.sleep(60)
        
        results = {}
        for i, (agent_type, _) in enumerate(tasks):
            r = await client.get(f"http://localhost:{8500+i}/result")
            results[agent_type] = r.json().get("result")
        
        return results

# Run it
results = asyncio.run(coordinated_task())
print(results)
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `ANTHROPIC_API_KEY` | Anthropic API key | Optional |
| `CLAWSWARM_PORT` | Orchestrator port | 8200 |
| `AGENT_BASE_PORT` | Starting port for agents | 8500 |

### Running as a Service (macOS)

```bash
# Create launchd plist
cat > ~/Library/LaunchAgents/com.clawswarm.api.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.clawswarm.api</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/clawswarm/.venv/bin/uvicorn</string>
        <string>src.clawswarm.api:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8200</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/clawswarm</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

# Load the service
launchctl load ~/Library/LaunchAgents/com.clawswarm.api.plist
```

## CLI Tool

Check swarm status from the command line:

```bash
python swarm-status.py
```

```
🦞 ClawSwarm Agent Status
┏━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name       ┃ Type     ┃ Status  ┃ Task                 ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ researcher │ research │ running │ Find AI trends...    │
│ writer     │ content  │ idle    │                      │
│ coder      │ coding   │ busy    │ Write Python code... │
│ devops     │ ops      │ running │ Create k8s yaml...   │
└────────────┴──────────┴─────────┴──────────────────────┘
Total: 4 agents | Running: 3 | Idle: 1 | Busy: 1
```

## License

MIT License - see [LICENSE](LICENSE)

## Contributing

Contributions welcome! Please read the contributing guidelines first.

## Credits

Built with ❤️ using [OpenClaw](https://github.com/openclaw/openclaw)
