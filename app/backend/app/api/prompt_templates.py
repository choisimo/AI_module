from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging

from app.models.prompt_template import PromptTemplate, PromptTemplateCreate
from app.services import prompt_template_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=PromptTemplate)
async def create_prompt_template(template_data: PromptTemplateCreate):
    """
    Create a new prompt template.
    """
    try:
        logger.info(f"Received request to create prompt template with name: {template_data.name}")
        # In a real scenario with DB, you might check for unique name constraints here
        # or let the DB layer handle it and catch the exception.
        # The simulated service currently doesn't strictly enforce unique names before adding to list.
        created_template = await prompt_template_service.create_template(template_data)
        logger.info(f"Prompt template '{created_template.name}' created successfully with ID: {created_template.id}")
        return created_template
    except Exception as e:
        logger.error(f"Error creating prompt template: {e}", exc_info=True)
        # Specific error handling can be added here, e.g., for duplicate names if service raised it
        raise HTTPException(status_code=500, detail="Failed to create prompt template.")

@router.get("/", response_model=List[PromptTemplate])
async def get_all_prompt_templates():
    """
    Retrieve all prompt templates.
    """
    try:
        logger.info("Received request to fetch all prompt templates.")
        templates = await prompt_template_service.get_templates()
        logger.info(f"Returning {len(templates)} prompt templates.")
        return templates
    except Exception as e:
        logger.error(f"Error fetching prompt templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve prompt templates.")

@router.get("/{template_id}", response_model=PromptTemplate)
async def get_prompt_template_by_id(template_id: int):
    """
    Retrieve a single prompt template by its ID.
    """
    try:
        logger.info(f"Received request to fetch prompt template with ID: {template_id}")
        template = await prompt_template_service.get_template_by_id(template_id)
        if not template:
            logger.warning(f"Prompt template with ID: {template_id} not found.")
            raise HTTPException(status_code=404, detail="Template not found")
        logger.info(f"Returning prompt template with ID: {template_id}")
        return template
    except HTTPException:
        raise # Re-raise HTTPException directly to preserve status code and detail
    except Exception as e:
        logger.error(f"Error fetching prompt template with ID {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve prompt template with ID {template_id}.")

@router.put("/{template_id}", response_model=PromptTemplate)
async def update_prompt_template(template_id: int, template_data: PromptTemplateCreate):
    """
    Update an existing prompt template.
    """
    try:
        logger.info(f"Received request to update prompt template with ID: {template_id}")
        updated_template = await prompt_template_service.update_template(template_id, template_data)
        if not updated_template:
            logger.warning(f"Prompt template with ID: {template_id} not found for update, or name conflict.")
            # The service layer now returns None for "not found" or "name conflict"
            # We need to check if it was a name conflict or truly not found.
            # For simplicity, we'll assume 404 for now if service returns None.
            # A more robust solution might have the service raise specific exceptions.
            existing_template = await prompt_template_service.get_template_by_id(template_id)
            if not existing_template:
                raise HTTPException(status_code=404, detail="Template not found")
            else:
                # This means the template was found, but update failed (e.g. name conflict)
                raise HTTPException(status_code=409, detail=f"Failed to update template: Name '{template_data.name}' may already exist.")
        logger.info(f"Prompt template with ID: {template_id} updated successfully.")
        return updated_template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt template with ID {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update prompt template with ID {template_id}.")

@router.delete("/{template_id}", response_model=dict)
async def delete_prompt_template(template_id: int):
    """
    Delete a prompt template by its ID.
    """
    try:
        logger.info(f"Received request to delete prompt template with ID: {template_id}")
        deleted = await prompt_template_service.delete_template(template_id)
        if not deleted:
            logger.warning(f"Prompt template with ID: {template_id} not found for deletion.")
            raise HTTPException(status_code=404, detail="Template not found")
        logger.info(f"Prompt template with ID: {template_id} deleted successfully.")
        return {"message": "Prompt template deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prompt template with ID {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete prompt template with ID {template_id}.")
