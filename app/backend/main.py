# FastAPI application entry point
from fastapi import FastAPI
from app.api import llm as llm_api
from app.api import prompt_templates as prompt_templates_api
from app.api import files as files_api
from app.api import jobs as jobs_api # Import the jobs router

app = FastAPI(title="My Application", version="1.0.0")

# Include the LLM API router
app.include_router(llm_api.router, prefix="/api/v1/llm", tags=["LLM"])

# Include the Prompt Templates API router
app.include_router(prompt_templates_api.router, prefix="/api/v1/prompt-templates", tags=["Prompt Templates"])

# Include the Files API router
app.include_router(files_api.router, prefix="/api/v1/files", tags=["Files"])

# Include the Jobs API router
app.include_router(jobs_api.router, prefix="/api/v1/jobs", tags=["Jobs"])

@app.get("/")
async def root():
    return {"message": "Hello World"}
