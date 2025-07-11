from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    # Database Configuration
    database_url: str = Field("postgres://postgres:postgres@localhost:54322/postgres", description="PostgreSQL database URL")

    # Application Configuration
    app_name: str = Field("PyScim", description="Application name")
    environment: str = Field("development", description="Environment (development, staging, production)")
    debug: bool = Field(True, description="Debug mode")
    log_level: str = Field("INFO", description="Logging level")

    # API Configuration
    api_prefix: str = Field("/scim/v2", description="API route prefix")
    cors_origins: List[str] = Field(["http://localhost:3000"], description="Allowed CORS origins")
    rate_limit_enabled: bool = Field(True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(100, description="Requests per minute limit")

    # Authentication
    auth_enabled: bool = Field(True, description="Enable API token authentication")

    # Pagination
    default_page_size: int = Field(100, description="Default page size")
    max_page_size: int = Field(1000, description="Maximum page size")

    # Server
    host: str = Field("0.0.0.0", description="Server host")
    port: int = Field(8000, description="Server port")
    reload: bool = Field(True, description="Enable auto-reload")

    @field_validator("environment")
    def validate_environment(cls, v: str) -> str:
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    @field_validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def tortoise_orm_config(self) -> dict:
        return {
            "connections": {"default": self.database_url},
            "apps": {
                "models": {
                    "models": ["scim.models"],
                    "default_connection": "default",
                }
            },
            "use_tz": True,
            "timezone": "UTC",
        }


# Create a singleton instance
settings = Settings()
