import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Body, Depends, BackgroundTasks # Added BackgroundTasks, Depends
from datetime import datetime
from uuid import uuid4

from app.models.job import SequentialJobCreate, SequentialJob, SequentialStep
# Import service modules and their factory functions
from app.services import job_service
from app.services.ollama_service import get_ollama_service # Assumes factory is defined
from app.services.prompt_template_service import get_prompt_template_service # Assumes factory is defined
# The actual service "instances" will be modules themselves if not classes.
# The Depends functions are placeholders for now if services are not classes.
# For job_service, we'll pass the module or specific functions.

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for jobs (for simulation)
_jobs_db: Dict[str, SequentialJob] = {}

@router.post("/sequential-jobs/", response_model=SequentialJob, status_code=202) # 202 for accepted for processing
async def create_sequential_job(
    job_create_request: SequentialJobCreate,
    background_tasks: BackgroundTasks,
    # The Depends calls will use the placeholder factories.
    # The actual service objects might be the modules themselves if not classes.
    # These are passed for conceptual completeness of dependency injection.
    # job_service.execute_sequential_job will use direct module imports for its calls.
    ollama_svc: Any = Depends(get_ollama_service), # Any for now as factory is no-op
    pt_svc: Any = Depends(get_prompt_template_service) # Any for now
):
    """
    Creates a new sequential LLM job and schedules it for background execution.
    The job is initially in a "pending" state.
    """
    logger.info(f"Received request to create sequential job with name: {job_create_request.job_name}")
    
    # Validate step dependencies
    step_ids_in_job = {step.step_id for step in job_create_request.steps}
    for step in job_create_request.steps:
        step_identifier = step.step_name if step.step_name else step.step_id
        if step.input_from_step:
            if step.input_from_step == step.step_id:
                raise HTTPException(status_code=422, detail=f"Step '{step_identifier}' cannot use its own output as input_from_step.")
            if step.input_from_step not in step_ids_in_job:
                logger.error(f"Validation error: Step '{step_identifier}' references non-existent step_id '{step.input_from_step}' for input_from_step.")
                raise HTTPException(
                    status_code=422,
                    detail=f"Step '{step_identifier}' references non-existent step_id '{step.input_from_step}' for input_from_step."
                )
        if step.file_content_from_step:
            if step.file_content_from_step == step.step_id:
                raise HTTPException(status_code=422, detail=f"Step '{step_identifier}' cannot use its own output as file_content_from_step.")
            if step.file_content_from_step not in step_ids_in_job:
                logger.error(f"Validation error: Step '{step_identifier}' references non-existent step_id '{step.file_content_from_step}' for file_content_from_step.")
                raise HTTPException(
                    status_code=422,
                    detail=f"Step '{step_identifier}' references non-existent step_id '{step.file_content_from_step}' for file_content_from_step."
                )

    new_job_id = str(uuid4())
    job = SequentialJob(
        job_id=new_job_id,
        job_name=job_create_request.job_name,
        steps=job_create_request.steps,
        status="pending", 
        step_outputs={},
        final_result=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    _jobs_db[new_job_id] = job
    job_service.set_jobs_db_ref(_jobs_db) # Pass the reference to the in-memory DB
    
    logger.info(f"Sequential job '{job.job_name}' (ID: {job.job_id}) created, status: {job.status}. Queued for execution.")
    
    # Add the job execution to background tasks
    # The service instances (ollama_svc, pt_svc) are passed here.
    # Since they are currently placeholder Depends, the job_service will use its module imports.
    # If these services were stateful classes, this DI would be critical.
    background_tasks.add_task(job_service.execute_sequential_job, job.job_id)
    
    logger.debug(f"Job Structure for ID {job.job_id}: {job.model_dump_json(indent=2)}")
    
    # Return 202 Accepted: The request has been accepted for processing,
    # but the processing has not been completed.
    return job

@router.get("/sequential-jobs/{job_id}", response_model=SequentialJob)
async def get_sequential_job(job_id: str):
    """
    Retrieves a sequential LLM job by its ID.
    """
    logger.info(f"Received request to fetch sequential job with ID: {job_id}")
    job = _jobs_db.get(job_id)
    if not job:
        logger.warning(f"Sequential job with ID: {job_id} not found.")
        raise HTTPException(status_code=404, detail="Sequential job not found")
    
    logger.info(f"Returning sequential job with ID: {job_id}")
    return job
