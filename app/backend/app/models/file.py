from pydantic import BaseModel, HttpUrl

class URLDownloadRequest(BaseModel):
    url: HttpUrl
