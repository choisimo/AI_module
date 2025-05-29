import logging
from typing import List
from app.models.prompt_template import PromptTemplate, PromptTemplateCreate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.models.prompt_template import LLMParams # Import LLMParams

# In-memory storage for simulation (will be replaced by DB)
_prompt_templates_db: List[PromptTemplate] = [
    PromptTemplate(id=1, name="Summarize Text", prompt_text="Summarize the following text:\n\n{text_input}", llm_params=LLMParams(temperature=0.7, top_k=50)),
    PromptTemplate(id=2, name="Translate to French", prompt_text="Translate the following text to French:\n\n{text_input}", llm_params=LLMParams(temperature=0.5)),
    PromptTemplate(id=3, name="General Question", prompt_text="Answer the following question:\n\n{question_input}", llm_params=None), # Example with no specific params
]
_next_id = 4 # Simulate auto-incrementing ID

async def create_template(template_data: PromptTemplateCreate) -> PromptTemplate:
    """
    Simulates saving a new prompt template.
    In a real application, this would save to a database.
    """
    global _next_id
    logger.info(f"Simulating creation of prompt template with name: {template_data.name}")
    
    # Simulate conflict for unique name (basic example)
    for existing_template in _prompt_templates_db:
        if existing_template.name == template_data.name:
            logger.warning(f"Prompt template with name '{template_data.name}' already exists.")
            # In a real scenario, you'd raise an HTTPException or similar
            # For now, let's just return the existing one or handle as an error indication
            # For simplicity of this simulation, we'll allow duplicates in the list for now
            # but in a real DB this would be a unique constraint.
            # To better simulate, let's just return the one found if names are meant to be unique
            # However, the task implies creating a new one or erroring.
            # Let's assume for now we just add it. The DB layer would handle uniqueness later.
            pass

    new_template = PromptTemplate(
        id=_next_id,
        name=template_data.name,
        prompt_text=template_data.prompt_text,
        llm_params=template_data.llm_params # Store llm_params
    )
    _prompt_templates_db.append(new_template)
    _next_id += 1
    logger.info(f"Prompt template '{new_template.name}' simulated creation with ID: {new_template.id}")
    return new_template

async def get_templates() -> List[PromptTemplate]:
    """
    Simulates fetching all prompt templates.
    In a real application, this would fetch from a database.
    """
    logger.info(f"Simulating fetching all prompt templates. Returning {_prompt_templates_db.__len__()} templates.")
    return _prompt_templates_db

async def get_template_by_id(template_id: int) -> PromptTemplate | None:
    """
    Simulates fetching a single prompt template by its ID.
    In a real application, this would fetch from a database.
    """
    logger.info(f"Simulating fetching prompt template with ID: {template_id}")
    for template in _prompt_templates_db:
        if template.id == template_id:
            return template
    logger.info(f"Prompt template with ID: {template_id} not found in simulation.")
    return None

async def update_template(template_id: int, template_update: PromptTemplateCreate) -> PromptTemplate | None:
    """
    Simulates updating an existing prompt template.
    In a real application, this would update in a database.
    """
    logger.info(f"Simulating update for prompt template with ID: {template_id}")
    for i, template in enumerate(_prompt_templates_db):
        if template.id == template_id:
            # Check for name conflict if the name is being changed
            if template.name != template_update.name:
                for existing_template in _prompt_templates_db:
                    if existing_template.id != template_id and existing_template.name == template_update.name:
                        logger.warning(f"Cannot update template ID {template_id}: name '{template_update.name}' already exists for template ID {existing_template.id}.")
                        # In a real app, this might raise a specific exception
                        return None # Or some indicator of conflict

            updated_template = PromptTemplate(
                id=template_id,
                name=template_update.name,
                prompt_text=template_update.prompt_text,
                llm_params=template_update.llm_params # Update llm_params
            )
            _prompt_templates_db[i] = updated_template
            logger.info(f"Prompt template with ID: {template_id} updated successfully.")
            return updated_template
    logger.warning(f"Prompt template with ID: {template_id} not found for update.")
    return None

async def delete_template(template_id: int) -> bool:
    """
    Simulates deleting a prompt template by its ID.
    In a real application, this would delete from a database.
    """
    logger.info(f"Simulating deletion for prompt template with ID: {template_id}")
    for i, template in enumerate(_prompt_templates_db):
        if template.id == template_id:
            del _prompt_templates_db[i]
            logger.info(f"Prompt template with ID: {template_id} deleted successfully.")
            return True
    logger.warning(f"Prompt template with ID: {template_id} not found for deletion.")
    return False

async def get_template_by_name(name: str) -> PromptTemplate | None:
    """
    Simulates fetching a single prompt template by its name.
    In a real application, this would fetch from a database.
    """
    logger.info(f"Simulating fetching prompt template with name: {name}")
    for template in _prompt_templates_db:
        if template.name == name:
            return template
    logger.info(f"Prompt template with name: {name} not found in simulation.")
    return None

# Placeholder for service factory if PromptTemplateService was a class
# class PromptTemplateService:
#   async def get_template_by_name(self, ...): ...
#   async def get_template_by_id(self, ...): ...
#   ... (other methods)
# def get_prompt_template_service():
#     return PromptTemplateService() # Or some more complex instantiation
# For now, since functions are module-level, this factory is a conceptual placeholder.
def get_prompt_template_service():
    """Placeholder factory for PromptTemplate service."""
    # Similar to get_ollama_service, this is a placeholder.
    # The actual service functions are used directly via module import in job_service.
    pass
