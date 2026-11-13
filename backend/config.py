from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore")
    app_env: Literal["development", "test", "production"] = "development"
    groq_api_key: SecretStr = SecretStr("")
    database_url: SecretStr = SecretStr("sqlite:///./traceforge.db")
    migration_database_url: SecretStr = SecretStr("")
    reasoning_model: str = "openai/gpt-oss-120b"
    efficient_model: str = "openai/gpt-oss-20b"
    verification_mode: Literal["local", "github", "unavailable"] = "unavailable"
    verification_unavailable_reason: str = ""
    admin_token: SecretStr = SecretStr("")
    session_secret: SecretStr = SecretStr("")
    github_token: SecretStr = SecretStr("")
    github_repository: str = ""
    github_ref: str = "main"
    daily_run_limit: int = 12
    session_run_limit: int = 2
    max_model_requests: int = 8
    max_tokens: int = 18000
    max_steps: int = 40
    max_duration_seconds: int = 600
    max_patch_attempts: int = 2
    max_concurrent_runs: int = 1
    max_body_bytes: int = 16384

    @property
    def effective_verification(self) -> Literal["local", "github", "unavailable"]:
        if self.app_env == "production" and self.verification_mode == "local":
            return "unavailable"
        if self.verification_mode == "github" and not (
            self.github_token.get_secret_value() and self.github_repository
        ):
            return "unavailable"
        return self.verification_mode


settings = Settings()
