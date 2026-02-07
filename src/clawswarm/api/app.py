"""FastAPI application for ClawSwarm orchestrator."""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from ..models import (
    Agent,
    AgentConfig,
    AgentType,
    SwarmStatus,
    TaskRequest,
    TaskResult,
)
from ..docker import DockerManager


# Global manager instance
_manager: Optional[DockerManager] = None


def get_manager() -> DockerManager:
    """Get the Docker manager instance."""
    global _manager
    if _manager is None:
        _manager = DockerManager()
    return _manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    global _manager
    _manager = DockerManager()
    yield
    # Shutdown - clean up agents
    for agent in await _manager.list_agents():
        if agent.status.value in ("running", "busy", "idle"):
            await _manager.kill_agent(agent.id)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="ClawSwarm",
        description="Agent swarm orchestrator for OpenClaw - spin up/down AI agents on demand",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS for MCP access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Health & Status ---

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "service": "clawswarm"}

    @app.get("/status", response_model=SwarmStatus)
    async def get_status():
        """Get overall swarm status."""
        manager = get_manager()
        agents = await manager.list_agents()
        
        running = sum(1 for a in agents if a.status.value == "running")
        idle = sum(1 for a in agents if a.status.value == "idle")
        busy = sum(1 for a in agents if a.status.value == "busy")
        
        return SwarmStatus(
            total_agents=len(agents),
            running_agents=running,
            idle_agents=idle,
            busy_agents=busy,
            agents=agents,
        )

    # --- Agent Management ---

    @app.post("/agents/spawn", response_model=Agent)
    async def spawn_agent(config: AgentConfig):
        """Spawn a new agent."""
        manager = get_manager()
        agent = await manager.spawn_agent(config)
        return agent

    @app.get("/agents", response_model=list[Agent])
    async def list_agents():
        """List all agents."""
        manager = get_manager()
        return await manager.list_agents()

    @app.get("/agents/{agent_id}", response_model=Agent)
    async def get_agent(agent_id: str):
        """Get a specific agent."""
        manager = get_manager()
        agent = await manager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    @app.delete("/agents/{agent_id}")
    async def kill_agent(agent_id: str):
        """Kill and remove an agent."""
        manager = get_manager()
        success = await manager.kill_agent(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found or failed to stop")
        return {"status": "killed", "agent_id": agent_id}

    # --- Task Management ---

    @app.post("/agents/{agent_id}/task")
    async def assign_task(agent_id: str, request: TaskRequest, background_tasks: BackgroundTasks):
        """Assign a task to an agent."""
        manager = get_manager()
        success = await manager.send_task(agent_id, request.task)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to assign task")
        return {"status": "assigned", "agent_id": agent_id, "task": request.task}

    @app.get("/agents/{agent_id}/result")
    async def get_result(agent_id: str):
        """Get the result from an agent."""
        manager = get_manager()
        result = await manager.get_result(agent_id)
        return {"agent_id": agent_id, "result": result}

    # --- Quick Actions ---

    @app.post("/quick/spawn/{agent_type}")
    async def quick_spawn(agent_type: AgentType, task: Optional[str] = None):
        """Quick spawn an agent by type."""
        manager = get_manager()
        config = AgentConfig(type=agent_type, task=task)
        agent = await manager.spawn_agent(config)
        return agent

    @app.post("/quick/run")
    async def quick_run(agent_type: AgentType, task: str):
        """Spawn an agent, run a task, return result, kill agent."""
        manager = get_manager()
        config = AgentConfig(type=agent_type, task=task, auto_terminate=True)
        agent = await manager.spawn_agent(config)
        
        # Wait for result (simplified - real impl would poll/webhook)
        # For now, just return the agent info
        return {
            "agent_id": agent.id,
            "status": "spawned",
            "task": task,
            "message": "Agent spawned and task assigned. Poll /agents/{id}/result for completion.",
        }

    @app.delete("/quick/killall")
    async def kill_all():
        """Kill all agents."""
        manager = get_manager()
        agents = await manager.list_agents()
        killed = 0
        for agent in agents:
            if await manager.kill_agent(agent.id):
                killed += 1
        return {"status": "complete", "killed": killed}

    # --- Agent Callbacks (called by agents) ---

    @app.post("/callback/{agent_id}/result")
    async def agent_callback_result(agent_id: str, result: TaskResult):
        """Receive result callback from an agent."""
        manager = get_manager()
        agent = await manager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Update agent with result
        agent.result = result.result
        agent.status = "idle"
        agent.last_activity = datetime.utcnow()
        
        return {"status": "received", "agent_id": agent_id}

    @app.post("/callback/{agent_id}/heartbeat")
    async def agent_callback_heartbeat(agent_id: str):
        """Receive heartbeat from an agent."""
        manager = get_manager()
        agent = await manager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        agent.last_activity = datetime.utcnow()
        return {"status": "ok"}

    # --- Wait for Agent ---

    @app.get("/agents/{agent_id}/wait")
    async def wait_for_agent(agent_id: str, timeout: float = 30.0):
        """Wait for an agent to become healthy."""
        manager = get_manager()
        agent = await manager.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        healthy = await manager.wait_for_agent(agent_id, timeout)
        return {
            "agent_id": agent_id,
            "healthy": healthy,
            "status": agent.status.value if agent else "unknown"
        }

    return app


# Create default app instance
app = create_app()
