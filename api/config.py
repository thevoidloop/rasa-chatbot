"""
Configuration settings for the API
"""
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App settings
    app_name: str = "RASA Training Platform API"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # Database
    database_url: str = "postgresql://rasa_user:rasa_password_2024@postgres:5432/rasa_chatbot"
    
    # Redis
    redis_url: str = "redis://redis:6379/0"
    
    # RASA
    rasa_url: str = "http://rasa-server:5005"
    
    # JWT
    secret_key: str = "tu_clave_secreta_super_segura_aqui_2024"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings():
    return Settings()
