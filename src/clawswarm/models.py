"""Data models for ClawSwarm."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Types of agents that can be spawned."""
    MARKETING = "marketing"
    RESEARCH = "research"
    CONTENT = "content"
    OPS = "ops"
    CODING = "coding"
    CUSTOM = "custom"


class AgentStatus(str, Enum):
    """Status of an agent."""
    STARTING = "starting"
    RUNNING = "running"
    BUSY = "busy"
    IDLE = "idle"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class AgentConfig(BaseModel):
    """Configuration for spawning an agent."""
    type: AgentType
    name: Optional[str] = None
    task: Optional[str] = None
    soul_override: Optional[str] = None  # Custom SOUL.md content
    memory_shared: bool = False  # Share memory with orchestrator
    auto_terminate: bool = True  # Kill when task complete
    timeout_minutes: int = 60


class Agent(BaseModel):
    """Represents a running agent."""
    id: str
    name: str
    type: AgentType
    status: AgentStatus
    container_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    task: Optional[str] = None
    last_activity: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None


class TaskRequest(BaseModel):
    """Request to assign a task to an agent."""
    agent_id: str
    task: str
    priority: int = 5  # 1-10, higher = more urgent
    callback_url: Optional[str] = None  # Webhook when done


class TaskResult(BaseModel):
    """Result from a completed task."""
    agent_id: str
    task: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class SwarmStatus(BaseModel):
    """Overall swarm status."""
    total_agents: int
    running_agents: int
    idle_agents: int
    busy_agents: int
    agents: list[Agent]
