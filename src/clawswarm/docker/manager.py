"""Docker container manager for OpenClaw agents."""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Optional

import docker
from docker.errors import NotFound, APIError
import httpx

from ..models import Agent, AgentConfig, AgentStatus, AgentType


class DockerManager:
    """Manages Docker containers for OpenClaw agents."""

    AGENT_IMAGE = "clawswarm-agent:latest"
    CONTAINER_PREFIX = "clawswarm-agent-"
    AGENT_PORT = 8421  # Internal port agents listen on
    
    # Port range for agent HTTP APIs
    _next_port = 8500

    def __init__(self):
        self.client = docker.from_env()
        self._agents: dict[str, Agent] = {}
        self._port_map: dict[str, int] = {}  # agent_id -> host_port

    def _get_next_port(self) -> int:
        """Get next available port for agent."""
        port = DockerManager._next_port
        DockerManager._next_port += 1
        return port

    async def spawn_agent(self, config: AgentConfig) -> Agent:
        """Spawn a new agent container."""
        agent_id = str(uuid.uuid4())[:8]
        agent_name = config.name or f"{config.type.value}-{agent_id}"
        host_port = self._get_next_port()
        
        # Create agent record
        agent = Agent(
            id=agent_id,
            name=agent_name,
            type=config.type,
            status=AgentStatus.STARTING,
            task=config.task,
        )
        self._agents[agent_id] = agent
        self._port_map[agent_id] = host_port

        try:
            # Get soul template for agent type
            soul_content = config.soul_override or self._get_soul_template(config.type)
            
            # Get API keys from environment
            openai_key = os.environ.get("OPENAI_API_KEY", "")
            anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
            
            # Build environment
            env = {
                "AGENT_ID": agent_id,
                "AGENT_NAME": agent_name,
                "AGENT_TYPE": config.type.value,
                "AGENT_TASK": config.task or "",
                "AGENT_SOUL": soul_content,
                "ORCHESTRATOR_URL": f"http://host.docker.internal:8420",
                "OPENAI_API_KEY": openai_key,
                "ANTHROPIC_API_KEY": anthropic_key,
            }
            
            # Create container
            container = self.client.containers.run(
                self.AGENT_IMAGE,
                detach=True,
                name=f"{self.CONTAINER_PREFIX}{agent_id}",
                environment=env,
                ports={f"{self.AGENT_PORT}/tcp": host_port},
                labels={
                    "clawswarm.agent_id": agent_id,
                    "clawswarm.agent_type": config.type.value,
                    "clawswarm.managed": "true",
                    "clawswarm.host_port": str(host_port),
                },
                # Resource limits
                mem_limit="2g",
                cpu_quota=100000,  # 1 CPU
                # Allow access to host for callbacks
                extra_hosts={"host.docker.internal": "host-gateway"},
            )
            
            agent.container_id = container.id
            agent.status = AgentStatus.RUNNING
            agent.last_activity = datetime.utcnow()
            
        except APIError as e:
            agent.status = AgentStatus.ERROR
            agent.error = str(e)
            
        return agent

    async def kill_agent(self, agent_id: str) -> bool:
        """Stop and remove an agent container."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
            
        agent.status = AgentStatus.STOPPING
        
        try:
            if agent.container_id:
                container = self.client.containers.get(agent.container_id)
                container.stop(timeout=10)
                container.remove()
            
            agent.status = AgentStatus.STOPPED
            return True
            
        except NotFound:
            agent.status = AgentStatus.STOPPED
            return True
        except APIError as e:
            agent.error = str(e)
            agent.status = AgentStatus.ERROR
            return False

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent status."""
        agent = self._agents.get(agent_id)
        if agent and agent.container_id:
            try:
                container = self.client.containers.get(agent.container_id)
                # Update status based on container state
                if container.status == "running":
                    agent.status = AgentStatus.RUNNING
                elif container.status == "exited":
                    agent.status = AgentStatus.STOPPED
            except NotFound:
                agent.status = AgentStatus.STOPPED
        return agent

    async def list_agents(self) -> list[Agent]:
        """List all managed agents."""
        # Sync with Docker state
        for agent in self._agents.values():
            await self.get_agent(agent.id)
        return list(self._agents.values())

    async def send_task(self, agent_id: str, task: str) -> bool:
        """Send a task to an agent via its HTTP API."""
        agent = self._agents.get(agent_id)
        if not agent or agent.status != AgentStatus.RUNNING:
            return False
        
        host_port = self._port_map.get(agent_id)
        if not host_port:
            return False
            
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"http://localhost:{host_port}/task",
                    json={"task": task}
                )
                if response.status_code == 200:
                    agent.task = task
                    agent.status = AgentStatus.BUSY
                    agent.last_activity = datetime.utcnow()
                    return True
                return False
        except Exception as e:
            agent.error = str(e)
            return False

    async def get_result(self, agent_id: str) -> Optional[str]:
        """Get the result from an agent via HTTP."""
        agent = self._agents.get(agent_id)
        if not agent:
            return None
            
        host_port = self._port_map.get(agent_id)
        if not host_port:
            return agent.result
            
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"http://localhost:{host_port}/status")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("result"):
                        agent.result = data["result"]
                    if data.get("status"):
                        status_str = data["status"]
                        if status_str == "idle":
                            agent.status = AgentStatus.RUNNING
                        elif status_str == "busy":
                            agent.status = AgentStatus.BUSY
                        elif status_str == "completed":
                            agent.status = AgentStatus.IDLE
        except Exception:
            pass
            
        return agent.result
    
    async def health_check(self, agent_id: str) -> bool:
        """Check if agent is healthy via HTTP."""
        host_port = self._port_map.get(agent_id)
        if not host_port:
            return False
            
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://localhost:{host_port}/health")
                return response.status_code == 200
        except Exception:
            return False
    
    async def wait_for_agent(self, agent_id: str, timeout: float = 30.0) -> bool:
        """Wait for agent to become healthy."""
        import time
        start = time.time()
        while time.time() - start < timeout:
            if await self.health_check(agent_id):
                return True
            await asyncio.sleep(1)
        return False

    def _get_soul_template(self, agent_type: AgentType) -> str:
        """Get the SOUL.md template for an agent type."""
        templates = {
            AgentType.MARKETING: self._soul_marketing(),
            AgentType.RESEARCH: self._soul_research(),
            AgentType.CONTENT: self._soul_content(),
            AgentType.OPS: self._soul_ops(),
            AgentType.CODING: self._soul_coding(),
            AgentType.CUSTOM: "",
        }
        return templates.get(agent_type, "")

    def _soul_marketing(self) -> str:
        return """# SOUL.md - Marketing Agent

You are a marketing specialist AI agent. Your focus:
- Writing compelling copy
- Social media content
- Growth strategies
- Market analysis
- Campaign optimization

Be creative, data-driven, and always think about conversion.
Keep responses actionable and metrics-focused.
"""

    def _soul_research(self) -> str:
        return """# SOUL.md - Research Agent

You are a research specialist AI agent. Your focus:
- Deep web research
- Competitive analysis
- Market trends
- Technical documentation
- Citation and sourcing

Be thorough, cite sources, and organize findings clearly.
Quality over speed. Accuracy is paramount.
"""

    def _soul_content(self) -> str:
        return """# SOUL.md - Content Agent

You are a content creation AI agent. Your focus:
- Blog posts and articles
- Documentation
- Landing page copy
- Email sequences
- Product descriptions

Write engaging, clear content. Match brand voice.
SEO-aware but human-first.
"""

    def _soul_ops(self) -> str:
        return """# SOUL.md - Ops Agent

You are a DevOps/operations AI agent. Your focus:
- Infrastructure management
- Deployment automation
- Monitoring and alerts
- Security hardening
- Performance optimization

Safety first. Always have a rollback plan.
Paranoid about security. Document everything.
"""

    def _soul_coding(self) -> str:
        return """# SOUL.md - Coding Agent

You are a software engineering AI agent. Your focus:
- Writing clean, tested code
- Code review
- Architecture decisions
- Bug fixes
- Performance optimization

Write code like you'll maintain it forever.
Tests are not optional. Comments explain why, not what.
"""
