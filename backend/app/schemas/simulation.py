from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class SimulationStatusResponse(BaseModel):
    status: str = Field(default="idle", description="Simulation status: idle, running, paused, stopped")
    version: str = Field(default="0.1.0", description="API and engine version")
    active_agents: int = Field(default=0, description="Count of currently active decentralized robot agents")
    ticks_elapsed: int = Field(default=0, description="Simulation ticks elapsed")
    grid_dimensions: Optional[Dict[str, int]] = Field(default=None, description="Current grid dimensions {width, height}")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional simulation runtime metadata")
