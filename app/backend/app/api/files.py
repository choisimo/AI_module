import logging
import os
import shutil
from typing import List
from uuid import uuid4

from fastapi import APIRouter, File, UploadFile, HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

from app.core.config import settings # Import the settings

# Ensure the upload directory exists (using settings.UPLOAD_DIR)
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload/")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Accepts one or more file uploads and saves them to the server.

    - **files**: A list of files to upload.
    """
    uploaded_filenames: List[str] = []
    errors: List[dict] = []

    for file in files:
        try:
            logger.info(f"Received file: {file.filename}, Content-Type: {file.content_type}, Size: {file.size}")

            # Security Note:
            # 1. Filename Validation: Original filenames should be sanitized or replaced.
            #    The current implementation uses the original filename, which can be a security risk
            #    (e.g., path traversal if not handled carefully, though os.path.join helps).
            #    A better approach is to generate a new filename (e.g., using UUID).
            # 2. Content-Type Validation: The content type provided by the client can be spoofed.
            #    For robust validation, use libraries like `python-magic` to determine the
            #    actual file type from its content.
            # 3. File Size Limits: Implement checks for maximum allowed file size to prevent
            #    Denial of Service (DoS) attacks. FastAPI's `UploadFile` and the web server (e.g., Uvicorn)
            #    might have their own limits, but application-level checks are also good.
            # 4. Large File Handling: For very large files, `file.read()` might consume a lot of memory.
            #    It's better to stream the file directly to disk, especially in production.
            #    `shutil.copyfileobj` is used here which is efficient.
            # 5. Error Handling: More granular error handling for disk full, permissions, etc.
            
            # Sanitize filename (basic example: replace spaces, use a UUID to avoid collisions)
            # For this iteration, we'll use a UUID + original extension.
            original_filename = file.filename if file.filename else "unknown_file"
            file_extension = os.path.splitext(original_filename)[1].lower() # Lowercase for consistent check
            client_content_type = file.content_type

            # Validate file type
            if not (file_extension in settings.ALLOWED_FILE_EXTENSIONS or \
                    (client_content_type and client_content_type in settings.ALLOWED_MIME_TYPES)):
                logger.warning(
                    f"File type not allowed for {original_filename}. Extension: '{file_extension}', "
                    f"MIME type: '{client_content_type}'"
                )
                errors.append({
                    "filename": original_filename,
                    "error": f"File type not supported. Allowed extensions: {settings.ALLOWED_FILE_EXTENSIONS} "
                             f"or MIME types: {settings.ALLOWED_MIME_TYPES}."
                })
                continue # Skip to the next file

            # Acknowledge collision risk if not using UUIDs:
            # If not using unique names, collisions can occur if multiple files with the same name are uploaded.
            # server_filename = original_filename 
            server_filename = f"{uuid4()}{file_extension}" # Use the validated (and lowercased) extension
            
            file_path = settings.UPLOAD_DIR / server_filename # Use settings.UPLOAD_DIR

            # Prevent directory traversal (though os.path.join and using a generated filename helps)
            if not str(file_path.resolve()).startswith(str(settings.UPLOAD_DIR.resolve())):
                logger.error(f"Potential directory traversal attempt for filename: {original_filename}")
                errors.append({"filename": original_filename, "error": "Invalid filename or path."})
                continue

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            uploaded_filenames.append(server_filename) # Or original_filename, or full path, depending on needs
            logger.info(f"Successfully saved file: {server_filename} to {file_path}")

        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}", exc_info=True)
            errors.append({"filename": file.filename if file.filename else "unknown_file", "error": str(e)})
        finally:
            # Ensure the file pointer is closed
            if hasattr(file, 'file') and not file.file.closed:
                file.file.close()

    if not uploaded_filenames and errors:
         # If all files failed, it might be better to return a different status code
         # For now, returning 200 with error details as per spec.
         pass

    return {"uploaded_files": uploaded_filenames, "errors": errors}

import httpx
import re
from app.models.file import URLDownloadRequest # Import the new model

@router.post("/download-url/")
async def download_file_from_url(request: URLDownloadRequest):
    """
    Downloads a file from the provided URL and saves it to the server.

    - **url**: The URL of the file to download.
    """
    url = str(request.url) # request.url is HttpUrl, convert to string for httpx
    logger.info(f"Received request to download file from URL: {url}")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client: # Added timeout
            try:
                response = await client.get(url)
                response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            except httpx.UnsupportedProtocol as e:
                logger.error(f"Invalid URL scheme for {url}: {e}")
                raise HTTPException(status_code=400, detail=f"Invalid URL scheme: {e}")
            except httpx.RequestError as e:
                logger.error(f"Error requesting file from URL {url}: {e}")
                # Distinguish between client-side (e.g. DNS failure) and server-side errors
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code >= 500:
                     raise HTTPException(status_code=502, detail=f"Remote server error downloading from URL: {e}") # Bad Gateway
                elif isinstance(e, httpx.HTTPStatusError) and e.response.status_code >= 400:
                     raise HTTPException(status_code=400, detail=f"Client error downloading from URL (e.g. not found): {e}")
                else: # Other request errors like DNS failure, connection timeout
                     raise HTTPException(status_code=504, detail=f"Error connecting to URL: {e}") # Gateway Timeout or similar

            # Determine filename
            # 1. Content-Disposition header
            content_disposition = response.headers.get("content-disposition")
            original_filename = None
            if content_disposition:
                # Example: "attachment; filename="example.txt""
                # More robust parsing might be needed for complex cases
                match = re.search(r'filename="?([^"]+)"?', content_disposition)
                if match:
                    original_filename = match.group(1)
            
            # 2. From URL path if not in Content-Disposition
            if not original_filename:
                url_path = request.url.path # Use the Pydantic HttpUrl's path attribute
                original_filename = os.path.basename(url_path) if url_path else "downloaded_file"

            # Basic sanitization and ensure there's a fallback name
            if not original_filename or original_filename == "/": # If path was just "/"
                original_filename = "downloaded_file_from_url"
            
            derived_file_extension = os.path.splitext(original_filename)[1].lower() # Lowercase for consistent check
            response_content_type = response.headers.get("content-type")

            # Validate downloaded file type (post-download)
            if not (derived_file_extension in settings.ALLOWED_FILE_EXTENSIONS or \
                    (response_content_type and response_content_type in settings.ALLOWED_MIME_TYPES)):
                logger.warning(
                    f"Downloaded file type not allowed from URL {url}. Original filename: {original_filename}, "
                    f"Derived extension: '{derived_file_extension}', Response MIME type: '{response_content_type}'"
                )
                # No file saved yet to delete, so just raise HTTP exception
                raise HTTPException(
                    status_code=400, 
                    detail=f"Downloaded file type is not supported. Extension: '{derived_file_extension}', "
                           f"MIME: '{response_content_type}'. Allowed extensions: {settings.ALLOWED_FILE_EXTENSIONS} "
                           f"or MIME types: {settings.ALLOWED_MIME_TYPES}."
                )

            # If no extension, try to guess from MIME (very basic, primarily for text)
            # This part is less critical if the MIME type itself is allowed.
            # If extension is empty AND MIME type is generic (e.g. application/octet-stream) but content is text,
            # this is where more advanced content inspection (e.g. python-magic) would be useful.
            # For now, if extension is missing but MIME type was allowed, we proceed.
            # If MIME was not allowed and extension was missing, it would have been caught above.
            
            # Use derived_file_extension (which is lowercased)
            server_filename = f"{uuid4()}{derived_file_extension if derived_file_extension else '.dat'}" 
            file_path = settings.UPLOAD_DIR / server_filename

            # Prevent directory traversal (already somewhat handled by os.path.join and generated filename)
            if not str(file_path.resolve()).startswith(str(settings.UPLOAD_DIR.resolve())):
                logger.error(f"Potential directory traversal for downloaded file from URL: {url} (original: {original_filename})")
                raise HTTPException(status_code=400, detail="Invalid filename derived from URL.")

            # Save the file
            file_content = await response.aread() # Reads the entire response body into memory
            
            # File has been downloaded, now write it.
            # If validation failed earlier, we wouldn't reach here.
            try:
                with open(file_path, "wb") as buffer:
                    buffer.write(file_content)
            except Exception as e_write: # Handle potential write errors
                logger.error(f"Error writing downloaded file {server_filename} to disk: {e_write}", exc_info=True)
                raise HTTPException(status_code=500, detail="Failed to save downloaded file to disk.")

            file_size = file_path.stat().st_size # Use Path.stat()
            logger.info(f"Successfully downloaded file from URL: {url}. Saved as: {server_filename}. Size: {file_size} bytes.")

            return {
                "message": "File downloaded successfully", 
                "filename": server_filename, 
                "original_url": url,
                "original_filename": original_filename, # The one derived from header/URL
                "filesize": file_size
            }

    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred downloading from URL {url}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
