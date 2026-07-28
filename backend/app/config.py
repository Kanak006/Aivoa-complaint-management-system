from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = ""
    groq_extraction_model: str = "llama-3.1-8b-instant"
    groq_reasoning_model: str = "openai/gpt-oss-120b"
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/aivoa_complaints"
    frontend_origin: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()
