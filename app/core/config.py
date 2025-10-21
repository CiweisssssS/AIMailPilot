from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    max_input_tokens: int = 12000
    summary_max_words: int = 20
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
