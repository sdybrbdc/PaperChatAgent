from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ServerSettings(BaseModel):
    name: str = "PaperChatAgent Backend"
    version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8000
    env: str = "dev"


class AuthSettings(BaseModel):
    secret_key: str = "paperchat-dev-secret-key-with-32-chars"
    access_token_ttl_seconds: int = 24 * 60 * 60
    refresh_token_ttl_seconds: int = 30 * 24 * 60 * 60
    access_cookie_name: str = "paperchat_access_token"
    refresh_cookie_name: str = "paperchat_refresh_token"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"


class MySQLSettings(BaseModel):
    endpoint: str = ""
    async_endpoint: str = ""


class VectorDBSettings(BaseModel):
    host: str = "127.0.0.1"
    port: str = "19530"
    mode: str = "chroma"


class OSSSettings(BaseModel):
    access_key_id: str = ""
    access_key_secret: str = ""
    endpoint: str = ""
    bucket_name: str = ""
    base_url: str = ""


class MinIOSettings(BaseModel):
    access_key_id: str = ""
    access_key_secret: str = ""
    endpoint: str = ""
    bucket_name: str = ""
    base_url: str = ""


class StorageSettings(BaseModel):
    mode: str = "minio"
    oss: OSSSettings = Field(default_factory=OSSSettings)
    minio: MinIOSettings = Field(default_factory=MinIOSettings)


class ModelEndpointSettings(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model_name: str = ""


class MultiModelsSettings(BaseModel):
    conversation_model: ModelEndpointSettings = Field(default_factory=ModelEndpointSettings)
    guidance_model: ModelEndpointSettings = Field(default_factory=ModelEndpointSettings)
    tool_call_model: ModelEndpointSettings = Field(default_factory=ModelEndpointSettings)
    reasoning_model: ModelEndpointSettings = Field(default_factory=ModelEndpointSettings)
    text2image: ModelEndpointSettings = Field(default_factory=ModelEndpointSettings)
    qwen_vl: ModelEndpointSettings = Field(default_factory=ModelEndpointSettings)
    embedding: ModelEndpointSettings = Field(default_factory=ModelEndpointSettings)
    rerank: ModelEndpointSettings = Field(default_factory=ModelEndpointSettings)


class AppSettings(BaseModel):
    server: ServerSettings = Field(default_factory=ServerSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    mysql: MySQLSettings = Field(default_factory=MySQLSettings)
    vector_db: VectorDBSettings = Field(default_factory=VectorDBSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    multi_models: MultiModelsSettings = Field(default_factory=MultiModelsSettings)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )


def _load_yaml_config() -> dict:
    def expand_env(value):
        if isinstance(value, str):
            return os.path.expandvars(value)
        if isinstance(value, list):
            return [expand_env(item) for item in value]
        if isinstance(value, dict):
            return {key: expand_env(item) for key, item in value.items()}
        return value

    config_path = Path(__file__).with_name("config.yaml")
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        return expand_env(yaml.safe_load(handle) or {})


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings.model_validate(_load_yaml_config())
