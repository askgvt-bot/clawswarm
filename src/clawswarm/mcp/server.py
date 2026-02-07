"""MCP (Model Context Protocol) server for ClawSwarm.

Exposes tools that can be called by AI agents to manage the swarm.
"""

import json
from typing import Any, Optional

import httpx


class MCPServer:
    """MCP server that wraps ClawSwarm API for tool access."""

    def __init__(self, api_url: str = "http://localhost:8420"):
        self.api_url = api_url
        self.client = httpx.AsyncClient(base_url=api_url, timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    # --- MCP Tool Definitions ---

    def get_tools(self) -> list[dict]:
        """Return MCP tool definitions."""
        return [
            {
                "name": "swarm_status",
                "description": "Get the current status of the agent swarm - how many agents running, idle, busy",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "swarm_spawn",
                "description": "Spawn a new agent. Types: marketing, research, content, ops, coding",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["marketing", "research", "content", "ops", "coding", "custom"],
                            "description": "Type of agent to spawn",
                        },
                        "name": {
                            "type": "string",
                            "description": "Optional name for the agent",
                        },
                        "task": {
                            "type": "string",
                            "description": "Initial task to assign",
                        },
                    },
                    "required": ["type"],
                },
            },
            {
                "name": "swarm_list",
                "description": "List all agents in the swarm",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "swarm_assign",
                "description": "Assign a task to an existing agent",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "ID of the agent",
                        },
                        "task": {
                            "type": "string",
                            "description": "Task to assign",
                        },
                    },
                    "required": ["agent_id", "task"],
                },
            },
            {
                "name": "swarm_result",
                "description": "Get the result from an agent's completed task",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "ID of the agent",
                        },
                    },
                    "required": ["agent_id"],
                },
            },
            {
                "name": "swarm_kill",
                "description": "Kill/stop an agent",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "ID of the agent to kill",
                        },
                    },
                    "required": ["agent_id"],
                },
            },
            {
                "name": "swarm_scale",
                "description": "Scale up - spawn multiple agents of a type",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["marketing", "research", "content", "ops", "coding"],
                            "description": "Type of agents to spawn",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of agents to spawn",
                            "minimum": 1,
                            "maximum": 10,
                        },
                    },
                    "required": ["type", "count"],
                },
            },
        ]

    # --- Tool Implementations ---

    async def call_tool(self, name: str, arguments: dict) -> Any:
        """Execute an MCP tool call."""
        handlers = {
            "swarm_status": self._status,
            "swarm_spawn": self._spawn,
            "swarm_list": self._list,
            "swarm_assign": self._assign,
            "swarm_result": self._result,
            "swarm_kill": self._kill,
            "swarm_scale": self._scale,
        }
        
        handler = handlers.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        
        return await handler(**arguments)

    async def _status(self) -> dict:
        """Get swarm status."""
        response = await self.client.get("/status")
        return response.json()

    async def _spawn(
        self,
        type: str,
        name: Optional[str] = None,
        task: Optional[str] = None,
    ) -> dict:
        """Spawn a new agent."""
        response = await self.client.post(
            "/agents/spawn",
            json={"type": type, "name": name, "task": task},
        )
        return response.json()

    async def _list(self) -> list:
        """List all agents."""
        response = await self.client.get("/agents")
        return response.json()

    async def _assign(self, agent_id: str, task: str) -> dict:
        """Assign a task to an agent."""
        response = await self.client.post(
            f"/agents/{agent_id}/task",
            json={"agent_id": agent_id, "task": task},
        )
        return response.json()

    async def _result(self, agent_id: str) -> dict:
        """Get result from an agent."""
        response = await self.client.get(f"/agents/{agent_id}/result")
        return response.json()

    async def _kill(self, agent_id: str) -> dict:
        """Kill an agent."""
        response = await self.client.delete(f"/agents/{agent_id}")
        return response.json()

    async def _scale(self, type: str, count: int) -> dict:
        """Scale up - spawn multiple agents."""
        agents = []
        for i in range(count):
            response = await self.client.post(
                "/agents/spawn",
                json={"type": type, "name": f"{type}-{i+1}"},
            )
            agents.append(response.json())
        return {"spawned": len(agents), "agents": agents}
