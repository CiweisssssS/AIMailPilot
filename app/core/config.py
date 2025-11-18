from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Legacy OpenAI settings (for backward compatibility)
    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_summary_model: Optional[str] = None
    openai_extractor_model: Optional[str] = None
    
    # Multi-provider API keys
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    
    # Default models for each service
    summarizer_model: str = "anthropic:claude-3-5-haiku"  # Default: Claude 3.5 Haiku
    extractor_model: str = "google:gemini-flash"  # Default: Gemini Flash
    extractor_fallback_model: str = "openai:gpt-4o-mini"  # Fallback for complex time: GPT-4o-mini
    
    max_input_tokens: int = 12000
    summary_max_words: int = 20
    work_end_hour: int = 17  # Default end-of-workday hour for EOD/date-only deadlines
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
