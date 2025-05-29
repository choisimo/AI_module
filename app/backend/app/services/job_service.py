import logging
from datetime import datetime
from typing import Dict, Optional
import os # For file operations

from app.models.job import SequentialJob, SequentialStep
from app.models.prompt_template import LLMParams # Assuming this is the correct model for LLM params
from app.services import ollama_service as ollama_svc_module # Direct module import
from app.services import prompt_template_service as pt_svc_module # Direct module import
from app.core.config import settings # For UPLOAD_DIR

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for jobs (mirrors the one in api/jobs.py for now, or could be passed around)
# This is problematic for a real app. Ideally, job status is updated in a shared DB.
# For this simulation, we'll assume the job object passed to execute_sequential_job
# is the one from api/jobs.py's _jobs_db.
_jobs_db_ref: Optional[Dict[str, SequentialJob]] = None

def set_jobs_db_ref(jobs_db: Dict[str, SequentialJob]):
    """
    Sets a reference to the jobs database (in-memory dict) used by the API layer.
    This is a workaround for in-memory simulation. In a real app, use a database.
    """
    global _jobs_db_ref
    _jobs_db_ref = jobs_db

async def execute_sequential_job(job_id: str): # Pass job_id, fetch job from shared store
    """
    Executes a sequential LLM job.
    This function is intended to be run as a background task.
    """
    if _jobs_db_ref is None:
        logger.error("Job DB reference not set in job_service. Cannot execute job.")
        return

    job = _jobs_db_ref.get(job_id)
    if not job:
        logger.error(f"Job with ID {job_id} not found in DB for execution.")
        return

    logger.info(f"Starting execution for job ID: {job.job_id}, Name: {job.job_name}")
    job.status = "running"
    job.updated_at = datetime.utcnow()
    job.step_outputs = {} # Initialize/clear previous outputs

    current_step_index = 0
    try:
        for i, job_step in enumerate(job.steps):
            current_step_index = i
            step_identifier = job_step.step_name if job_step.step_name else job_step.step_id
            logger.info(f"Executing Step {i+1}/{len(job.steps)}: ID '{job_step.step_id}', Name: '{step_identifier}' for job '{job.job_id}'")

            current_prompt_text: str = ""
            current_file_content: Optional[str] = None
            # Priority for LLM params: Step-specific > Template-specific > None
            effective_llm_params: Optional[LLMParams] = job_step.llm_params 
            
            input_from_previous_step_output: Optional[str] = None

            # Handle input_from_step
            if job_step.input_from_step:
                if job_step.input_from_step in job.step_outputs:
                    input_from_previous_step_output = job.step_outputs[job_step.input_from_step]
                    logger.info(f"Step '{step_identifier}': Using output from step '{job_step.input_from_step}' as text input.")
                else:
                    raise ValueError(f"Step '{job_step.input_from_step}' output not found for step '{step_identifier}'.")

            # Handle prompt_template_name
            if job_step.prompt_template_name:
                template = await pt_svc_module.get_template_by_name(job_step.prompt_template_name)
                if template:
                    current_prompt_text = template.prompt_text
                    if effective_llm_params is None: # If step has no params, use template's
                        effective_llm_params = template.llm_params
                    logger.info(f"Step '{step_identifier}': Loaded prompt from template '{job_step.prompt_template_name}'.")
                else:
                    raise ValueError(f"Prompt template '{job_step.prompt_template_name}' not found for step '{step_identifier}'.")
            
            # Handle prompt_text (overrides template's text or is used directly)
            if job_step.prompt_text:
                current_prompt_text = job_step.prompt_text # Override if both template and direct text exist
                logger.info(f"Step '{step_identifier}': Using direct prompt_text.")

            # Combine previous output with prompt (simple placeholder replacement or prepending)
            if input_from_previous_step_output:
                if "{input}" in current_prompt_text: # Requires templates to use "{input}"
                    current_prompt_text = current_prompt_text.replace("{input}", input_from_previous_step_output)
                else: # Fallback to prepending if placeholder not found
                    current_prompt_text = f"{input_from_previous_step_output}\n\n{current_prompt_text}"
                logger.info(f"Step '{step_identifier}': Combined previous step output into prompt.")
            
            # Handle file_input_ref (e.g., filename of an uploaded file)
            if job_step.file_input_ref:
                file_path = settings.UPLOAD_DIR / job_step.file_input_ref
                try:
                    if file_path.is_file():
                        with open(file_path, "r", encoding="utf-8") as f:
                            current_file_content = f.read()
                        logger.info(f"Step '{step_identifier}': Loaded file content from '{job_step.file_input_ref}'.")
                    else:
                        raise ValueError(f"File '{job_step.file_input_ref}' not found at path '{file_path}' for step '{step_identifier}'.")
                except Exception as e_file:
                    raise ValueError(f"Error reading file '{job_step.file_input_ref}' for step '{step_identifier}': {e_file}")

            # Handle file_content_from_step (overrides file_input_ref if both are present)
            if job_step.file_content_from_step:
                if job_step.file_content_from_step in job.step_outputs:
                    current_file_content = job.step_outputs[job_step.file_content_from_step]
                    logger.info(f"Step '{step_identifier}': Using output from step '{job_step.file_content_from_step}' as file content.")
                else:
                    raise ValueError(f"Step '{job_step.file_content_from_step}' output not found to be used as file content for step '{step_identifier}'.")

            # Iterative execution for the step
            current_step_output_for_iteration = ""
            base_prompt_for_step = current_prompt_text # Save the initial prompt for the step
            
            for iteration_count in range(job_step.iterations):
                iter_log_prefix = f"Step '{step_identifier}' Iteration {iteration_count + 1}/{job_step.iterations}"
                logger.info(f"{iter_log_prefix}: Starting.")

                iterative_prompt_text = base_prompt_for_step
                if iteration_count > 0: # Not the first iteration
                    # Apply iteration_prompt_strategy. For now, simple "refine" by appending.
                    if job_step.iteration_prompt_strategy == "refine" or job_step.iteration_prompt_strategy is None: # Default to refine
                        iterative_prompt_text = f"{base_prompt_for_step}\n\nPrevious attempt output:\n{current_step_output_for_iteration}\n\nPlease refine or continue based on the previous attempt."
                        logger.info(f"{iter_log_prefix}: Applied 'refine' strategy, appended previous output to prompt.")
                    # Add other strategies like "continue" (which might be similar to refine or use different phrasing)
                    # or strategies that might ignore base_prompt_for_step after first iteration.
                    # For now, only "refine" is explicitly handled by appending.
                
                # Context Chunking Logic - applied per iteration if context strategy is active
                # The current_file_content is the full file content.
                # If chunking is enabled, we process this file content in chunks.
                
                final_output_for_this_iteration = "" # Output of this specific iteration (might be from one chunk or concatenated chunks)

                if job_step.context_strategy == "chunk_and_concatenate" and \
                   current_file_content is not None and \
                   job_step.chunk_size is not None and job_step.chunk_size > 0:
                    
                    logger.info(f"{iter_log_prefix}: Applying 'chunk_and_concatenate' context strategy. Chunk size: {job_step.chunk_size}, Overlap: {job_step.chunk_overlap}")
                    chunks = _chunk_text(current_file_content, job_step.chunk_size, job_step.chunk_overlap or 0)
                    aggregated_chunk_llm_outputs = []

                    for chunk_idx, text_chunk in enumerate(chunks):
                        chunk_log_prefix = f"{iter_log_prefix}, Chunk {chunk_idx + 1}/{len(chunks)}"
                        logger.info(f"{chunk_log_prefix}: Processing.")
                        
                        # LLM call for this specific chunk
                        success, response_data_chunk = await ollama_svc_module.generate_llm_response(
                            model_name=job_step.model_name,
                            prompt=iterative_prompt_text, # The prompt (potentially modified by iteration strategy)
                            file_content=text_chunk,      # The current chunk of the file
                            stream=False, 
                            llm_params=effective_llm_params 
                        )

                        if not success or not isinstance(response_data_chunk, str):
                            error_message = str(response_data_chunk) if not success else "Invalid response type from LLM service for chunk."
                            raise Exception(f"{chunk_log_prefix}: LLM call failed: {error_message}")
                        
                        aggregated_chunk_llm_outputs.append(response_data_chunk)
                        logger.info(f"{chunk_log_prefix}: Chunk processing successful.")

                    final_output_for_this_iteration = "\n\n---\n\n".join(aggregated_chunk_llm_outputs)
                    logger.info(f"{iter_log_prefix}: All {len(chunks)} chunks processed and concatenated.")
                
                else: # No chunking, or no file content, or chunk_size not set
                    # This is the normal path if context_strategy is "none" or file content is not applicable
                    # current_file_content remains the full file content (or None)
                    logger.info(f"{iter_log_prefix}: Calling Ollama model '{job_step.model_name}' (no chunking or no file content for chunking).")
                    success, response_data_single_call = await ollama_svc_module.generate_llm_response(
                        model_name=job_step.model_name,
                        prompt=iterative_prompt_text,
                        file_content=current_file_content, # Full file content or None
                        stream=False, 
                        llm_params=effective_llm_params 
                    )

                    if not success or not isinstance(response_data_single_call, str):
                        error_message = str(response_data_single_call) if not success else "Invalid response type from LLM service."
                        raise Exception(f"{iter_log_prefix}: LLM call failed: {error_message}")
                    
                    final_output_for_this_iteration = response_data_single_call

                # current_step_output_for_iteration is the result of this full iteration
                # (which might include concatenated chunk results or a single call result)
                current_step_output_for_iteration = final_output_for_this_iteration
                logger.info(f"{iter_log_prefix}: Iteration successful. Output captured.")
                # logger.debug(f"{iter_log_prefix} Output: {current_step_output_for_iteration[:200]}...")


            # After all iterations for the step are complete
            job.step_outputs[job_step.step_id] = current_step_output_for_iteration
            job.final_result = current_step_output_for_iteration # Update final_result with the latest step's output
            job.updated_at = datetime.utcnow()
            logger.info(f"Step '{step_identifier}' (all {job_step.iterations} iterations) executed successfully. Final output stored.")

        job.status = "completed"
        logger.info(f"Job ID: {job.job_id} completed successfully. Final result stored.")

    except ValueError as ve: # Specific validation/setup errors
        job.status = "failed"
        error_msg = f"Error in step {current_step_index + 1} ('{job.steps[current_step_index].step_name if job.steps[current_step_index].step_name else job.steps[current_step_index].step_id}'): {str(ve)}"
        job.final_result = error_msg
        logger.error(f"Job ID: {job.job_id} failed. {error_msg}", exc_info=True)
    except Exception as e: # Catch-all for other unexpected errors during execution
        job.status = "failed"
        error_msg = f"Unexpected error during execution of step {current_step_index + 1} ('{job.steps[current_step_index].step_name if job.steps[current_step_index].step_name else job.steps[current_step_index].step_id}'): {str(e)}"
        job.final_result = error_msg
        logger.error(f"Job ID: {job.job_id} failed. {error_msg}", exc_info=True)
    
    job.updated_at = datetime.utcnow()
    # Update the job in the shared store (important for in-memory simulation)
    if _jobs_db_ref is not None:
         _jobs_db_ref[job.job_id] = job
    else: # Should not happen if set_jobs_db_ref was called
        logger.error(f"Job DB reference is None. Cannot update job {job.job_id} status post-execution.")


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """
    Splits text into chunks with specified size and overlap.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative.")
    if chunk_overlap >= chunk_size:
        # This validation is also in the Pydantic model, but good to have here too.
        raise ValueError("chunk_overlap must be less than chunk_size.")

    chunks = []
    start_index = 0
    while start_index < len(text):
        end_index = start_index + chunk_size
        chunks.append(text[start_index:end_index])
        start_index += chunk_size - chunk_overlap
        if start_index >= len(text) and chunks[-1] != text[start_index - (chunk_size - chunk_overlap):]: # Avoid infinite loop on zero-step
             # This condition means the last chunk didn't make progress or is a repeat.
             # This can happen if chunk_size - chunk_overlap is 0 and we are at the end.
             # However, with overlap < chunk_size, step will be > 0.
             # Ensure we don't get stuck if len(text) is small or overlap is large.
             # The main loop condition `start_index < len(text)` should handle most cases.
             # One specific case: if the remaining text is smaller than chunk_size but start_index is still valid.
             # The slicing `text[start_index:end_index]` handles this gracefully by taking up to end of string.
             pass 
    
    # Ensure the very last part of the text is included if overlap logic caused it to be missed
    # This is usually handled by the while loop and slicing, but let's consider edge cases.
    # For example, if text = "abc", size=2, overlap=0 -> ["ab", "c"]
    # if text = "abc", size=2, overlap=1 -> ["ab", "bc"]
    # The current logic `start_index += chunk_size - chunk_overlap` should correctly cover.
    return chunks

# Note on service structure (as in previous version):
# OllamaService and PromptTemplateService are modules. execute_sequential_job uses their functions.
# Placeholder factories exist but are not strictly necessary for this service-to-service interaction.
# The `set_jobs_db_ref` is for in-memory simulation.
