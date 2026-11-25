from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["healthy"])
    service: str = Field(..., examples=["PrepAI"])
    environment: str = Field(..., examples=["development"])
    version: str = Field(..., examples=["0.1.0"])
