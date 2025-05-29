import httpx
import logging
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/tags"

async def get_ollama_models() -> List[str]:
    """
    Fetches the list of available LLM models from a local Ollama server.

    Returns:
        A list of model names. Returns an empty list if an error occurs.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(OLLAMA_API_URL)
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            
            data = response.json()
            models = [model.get("name") for model in data.get("models", []) if model.get("name")]
            return models
            
    except httpx.RequestError as e:
        logger.error(f"Error fetching Ollama models: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching models: {e}")
        return []

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"

from typing import AsyncGenerator, Tuple, Union, Optional, Dict, Any
import json
from app.models.prompt_template import LLMParams # Import LLMParams

async def generate_llm_response(
    model_name: str, 
    prompt: str, 
    stream: bool = False, 
    file_content: Optional[str] = None,
    llm_params: Optional[LLMParams] = None
) -> Tuple[bool, Union[str, AsyncGenerator[str, None]]]:
    """
    Sends a prompt to a specified Ollama LLM model and receives its response.

    Args:
        model_name: The name of the Ollama model to use.
        prompt: The prompt text to send to the model.
        stream: Whether to stream the response or wait for the full response.
        file_content: Optional content of a file to be prepended to the prompt.
        llm_params: Optional LLM parameters to use for generation.

    Returns:
        A tuple containing:
        - bool: True if successful, False otherwise.
        - Union[str, AsyncGenerator[str, None]]: 
            - If stream is False and successful: The full generated text (str).
            - If stream is True and successful: An asynchronous generator (AsyncGenerator[str, None]) yielding response chunks.
            - If unsuccessful: An error message (str).
    """
    final_prompt = prompt
    if file_content:
        final_prompt = f"File Content:\n{file_content}\n\nUser Prompt:\n{prompt}"

    payload: Dict[str, Any] = {
        "model": model_name,
        "prompt": final_prompt,
        "stream": stream,
    }

    if llm_params:
        # Add llm_params to the 'options' key, excluding None values
        options = {k: v for k, v in llm_params.model_dump().items() if v is not None}
        if options: # Only add 'options' key if there are actual parameters to set
            payload["options"] = options

    try:
        async with httpx.AsyncClient(timeout=None) as client: # Disable timeout for potentially long streams
            async with client.stream("POST", OLLAMA_GENERATE_URL, json=payload) as response:
                response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
                
                if not stream:
                    # Non-streaming: accumulate the full response
                    full_response_content = ""
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            try:
                                # Ollama's non-streaming response might be a single JSON object
                                # or multiple JSON objects if something unexpected happens.
                                # We try to parse it as a whole first.
                                # If it's line-delimited JSON, this might fail,
                                # so we also handle line-by-line parsing.
                                data = json.loads(chunk.decode('utf-8'))
                                if "response" in data:
                                     full_response_content += data["response"]
                                # If the response is a final, single JSON object, it might also contain 'done':true
                                if data.get("done"):
                                    break 
                            except json.JSONDecodeError:
                                # Fallback for potentially line-delimited JSON in non-streaming mode
                                # (though typically Ollama sends a single JSON object for non-streaming)
                                lines = chunk.decode('utf-8').splitlines()
                                for line in lines:
                                    if line:
                                        try:
                                            data = json.loads(line)
                                            if "response" in data:
                                                full_response_content += data["response"]
                                            if data.get("done"): # check for 'done' if it's part of the line
                                                break
                                        except json.JSONDecodeError:
                                            logger.warning(f"Failed to decode JSON line in non-streaming mode: {line}")
                                if data.get("done"): # if the last processed chunk indicated completion
                                    break
                    return True, full_response_content.strip()
                else:
                    # Streaming: return an async generator
                    async def response_generator():
                        async for chunk in response.aiter_lines():
                            if chunk:
                                try:
                                    data = json.loads(chunk)
                                    if "response" in data:
                                        yield data["response"]
                                    if data.get("done"): # Check if the model is done streaming
                                        break
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to decode JSON stream chunk: {chunk}")
                    return True, response_generator()

    except httpx.RequestError as e:
        logger.error(f"Error generating LLM response (model: {model_name}): {e}")
        return False, f"Error connecting to Ollama: {e}"
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error generating LLM response (model: {model_name}): {e.response.status_code} - {e.response.text}")
        return False, f"Ollama API error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        logger.error(f"An unexpected error occurred while generating LLM response (model: {model_name}): {e}")
        return False, f"An unexpected error occurred: {str(e)}"

# Placeholder for service factory if OllamaService was a class
# class OllamaService:
#     async def generate_llm_response(self, ...): ...
# def get_ollama_service():
#     return OllamaService() # Or some more complex instantiation
# For now, since functions are module-level, this factory is a conceptual placeholder.
# If FastAPI's Depends needs a callable that returns the "service" (the module itself),
# this could be: `def get_ollama_service(): return ollama_service_module` (where module is imported)
# For this task, the job_service will import ollama_service directly.
# The API layer might use this factory for Depends if needed.
# For now, it will be a no-op function.
def get_ollama_service():
    """Placeholder factory for Ollama service."""
    # In a class-based approach, this would return an instance of OllamaService.
    # Since we are using module-level functions, this factory doesn't do much.
    # The actual service functions are used directly via module import.
    # If Depends strictly needs a return, one might return the module itself,
    # but often direct imports are cleaner for module-only services.
    # For the purpose of the task, we'll make it a no-op.
    pass
