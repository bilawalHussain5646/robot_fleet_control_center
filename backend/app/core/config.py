from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Robot Fleet Control Center"
    database_url: str = "sqlite:///./robot_fleet.db"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "dev-only-change-me"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    cors_origins: str = "http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:8080"
    simulation_enabled: bool = True
    simulation_robot_count: int = 10
    simulation_update_interval: float = 1
    telemetry_storage_interval: int = 5
    openai_api_key: str | None = None
    ai_model: str = "mock"
    class Config:
        env_file = ".env"
        case_sensitive = False
settings = Settings()
