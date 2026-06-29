from pydantic import BaseModel, Field

class Task(BaseModel):
    agent: str = Field(description="The agent to execute next (content_strategist, communicator, or vector_search_agent)")
    done: bool = Field(default=False, description="Whether the task is completed")
    description: str = Field(description="Description of the task to be performed")
    done_at: str = Field(default="", description="Timestamp when the task was completed")
