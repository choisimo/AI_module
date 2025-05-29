from pydantic import BaseModel, validator, Field, root_validator
from typing import Optional, List, Dict, Literal
from datetime import datetime
from uuid import uuid4

from app.models.prompt_template import LLMParams # Ensure LLMParams is importable

class SequentialStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique identifier for the step, can be client-provided or auto-generated.")
    step_name: Optional[str] = None # Added for easier identification
    iterations: int = Field(default=1, ge=1, description="Number of times this step should iterate. Must be >= 1.")
    iteration_prompt_strategy: Optional[str] = Field(None, description="Strategy for modifying prompt in iterations (e.g., 'refine').") # e.g., "refine", "continue"
    
    # Context Management
    ContextManagementStrategy = Literal["none", "chunk_and_concatenate"]
    context_strategy: ContextManagementStrategy = Field(default="none", description="Strategy for handling large file context.")
    chunk_size: Optional[int] = Field(None, description="Size of chunks for context management (e.g., characters).")
    chunk_overlap: int = Field(default=0, ge=0, description="Overlap between chunks. Must be non-negative.")

    model_name: str
    prompt_template_name: Optional[str] = None
    prompt_text: Optional[str] = None
    file_input_ref: Optional[str] = None # e.g., filename of an uploaded file
    llm_params: Optional[LLMParams] = None
    
    # References to outputs of other steps
    input_from_step: Optional[str] = None 
    file_content_from_step: Optional[str] = None

    @validator('prompt_text', always=True)
    def check_prompt_source(cls, v, values):
        if not values.get('prompt_template_name') and not v:
            raise ValueError('Either prompt_template_name or prompt_text must be provided for a step.')
        return v

    @root_validator
    def check_chunking_params(cls, values):
        strategy = values.get('context_strategy')
        chunk_size = values.get('chunk_size')
        chunk_overlap = values.get('chunk_overlap')

        if strategy == "chunk_and_concatenate":
            if chunk_size is None or chunk_size <= 0:
                raise ValueError("If context_strategy is 'chunk_and_concatenate', chunk_size must be a positive integer.")
            if chunk_overlap is not None and chunk_overlap >= chunk_size : # chunk_overlap already has ge=0
                raise ValueError("chunk_overlap must be less than chunk_size.")
        return values

class SequentialJobCreate(BaseModel):
    job_name: Optional[str] = None
    steps: List[SequentialStep]

class SequentialJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    job_name: Optional[str] = None
    status: str = "pending" # Default status
    steps: List[SequentialStep]
    step_outputs: Optional[Dict[str, str]] = None
    final_result: Optional[str] = None # Could be the output of the last step
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True # For SQLAlchemy model compatibility later if needed
        # For Pydantic v2, use `model_config = {"from_attributes": True}` if migrating
