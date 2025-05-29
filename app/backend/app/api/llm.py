from fastapi import APIRouter, HTTPException
from typing import List
import logging

from app.services.ollama_service import get_ollama_models

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/models", response_model=List[str])
async def list_llm_models():
    """
    Endpoint to get the list of available LLM models from Ollama.
    """
    try:
        models = await get_ollama_models()
        if not models:
            # This case could mean either no models are available or an error occurred.
            # The service function already logs errors.
            # Depending on desired API behavior, you might want to distinguish
            # "no models available" from "error fetching models".
            # For now, returning an empty list is consistent.
            pass
        return models
    except Exception as e:
        logger.error(f"Error in /models endpoint: {e}")
        # Re-raise HTTPException to ensure FastAPI handles it correctly
        # and returns a 500 error to the client.
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching models.")

from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from app.services.ollama_service import generate_llm_response
from typing import AsyncGenerator

from typing import Optional # Ensure Optional is imported

from app.models.prompt_template import LLMParams # Import LLMParams

class LLMGenerateRequest(BaseModel):
    model_name: str
    prompt: str
    stream: bool = False
    file_content: Optional[str] = None
    llm_params: Optional[LLMParams] = None # Add llm_params field

@router.post("/generate")
async def generate_llm_output(request: LLMGenerateRequest):
    """
    Endpoint to generate a response from a specified LLM model.
    Can operate in streaming or non-streaming mode, include file content, and custom LLM parameters.
    """
    success, response_data = await generate_llm_response(
        request.model_name,
        request.prompt,
        request.stream,
        request.file_content,
        request.llm_params # Pass llm_params to the service
    )

    if not success:
        # response_data contains the error message from the service
        raise HTTPException(status_code=500, detail=str(response_data))

    if request.stream:
        if not isinstance(response_data, AsyncGenerator):
            # This should ideally not happen if service is implemented correctly
            logger.error("Streaming mode requested, but service did not return an AsyncGenerator.")
            raise HTTPException(status_code=500, detail="Internal server error: Streaming misconfiguration.")
        
        # Ensure the generator is correctly structured for StreamingResponse
        async def stream_response_content():
            try:
                async for chunk in response_data:
                    yield chunk
            except Exception as e:
                # Log the error during streaming
                logger.error(f"Error during response streaming: {e}")
                # You might want to signal the client that an error occurred if possible,
                # though with raw streaming, it's tricky.
                # For now, the stream will just stop.
                # Consider how to handle this based on client expectations.
                pass 
        return StreamingResponse(stream_response_content(), media_type="text/plain")
    else:
        # Non-streaming: response_data is the full text (str)
        if not isinstance(response_data, str):
            logger.error("Non-streaming mode, but service did not return a string.")
            raise HTTPException(status_code=500, detail="Internal server error: Non-streaming response error.")
        return {"response": response_data}
