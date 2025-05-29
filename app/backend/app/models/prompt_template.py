from pydantic import BaseModel, Field
from typing import Optional, List

class LLMParams(BaseModel):
    temperature: Optional[float] = Field(None, description="Controls randomness: higher values increase diversity.")
    top_k: Optional[int] = Field(None, description="Reduces the probability mass function to the K most likely tokens.")
    top_p: Optional[float] = Field(None, description="Filters using cumulative probability, selecting from the smallest set of tokens whose cumulative probability exceeds P.")
    num_predict: Optional[int] = Field(None, description="Maximum number of tokens to predict.")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility.")
    stop: Optional[List[str]] = Field(None, description="Sequences at which the model will stop generating.")
    # Add other parameters as needed, e.g.:
    # repeat_last_n: Optional[int] = Field(None, description="Number of last tokens to penalize repetitions of.")
    # repeat_penalty: Optional[float] = Field(None, description="Penalty for repeating tokens.")
    # presence_penalty: Optional[float] = Field(None, description="Penalty for new tokens based on whether they appear in the text so far.")
    # frequency_penalty: Optional[float] = Field(None, description="Penalty for new tokens based on their existing frequency in the text so far.")
    # mirostat: Optional[int] = Field(None, description="Enable Mirostat sampling (0=disabled, 1=Mirostat, 2=Mirostat 2.0).")
    # mirostat_tau: Optional[float] = Field(None, description="Mirostat learning rate.")
    # mirostat_eta: Optional[float] = Field(None, description="Mirostat target entropy.")
    # tfs_z: Optional[float] = Field(None, description="Tail Free Sampling Z parameter.")
    # num_ctx: Optional[int] = Field(None, description="Context window size.")

class PromptTemplateBase(BaseModel):
    name: str
    prompt_text: str
    llm_params: Optional[LLMParams] = None

class PromptTemplateCreate(PromptTemplateBase):
    pass

class PromptTemplate(PromptTemplateBase):
    id: int

    class Config:
        from_attributes = True
