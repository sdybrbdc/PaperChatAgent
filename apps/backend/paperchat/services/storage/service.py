from __future__ import annotations

from io import BytesIO
from urllib.parse import urlparse
from uuid import uuid4

from minio import Minio

from paperchat.api.errcode import AppError
from paperchat.settings import get_settings


class StorageService:
    def _build_minio_client(self) -> Minio:
        settings = get_settings()
        config = settings.storage.minio
        endpoint = config.endpoint
        secure = endpoint.startswith("https://")
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            endpoint = urlparse(endpoint).netloc
        return Minio(
            endpoint,
            access_key=config.access_key_id,
            secret_key=config.access_key_secret,
            secure=secure,
        )

    def _ensure_bucket(self, client: Minio) -> str:
        settings = get_settings()
        bucket_name = settings.storage.minio.bucket_name
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
        return bucket_name

    def upload_bytes(self, *, filename: str, content_type: str, data: bytes, object_key: str | None = None) -> dict:
        settings = get_settings()
        if settings.storage.mode != "minio":
            raise AppError(status_code=400, code="INTERNAL_ERROR", message="当前仅实现 MinIO 上传")

        client = self._build_minio_client()
        bucket_name = self._ensure_bucket(client)
        object_key = object_key or f"uploads/{uuid4()}-{filename}"
        client.put_object(
            bucket_name,
            object_key,
            BytesIO(data),
            length=len(data),
            content_type=content_type or "application/octet-stream",
        )

        base_url = settings.storage.minio.base_url.rstrip("/")
        return {
            "object_key": object_key,
            "bucket_name": bucket_name,
            "url": f"{base_url}/{object_key}",
        }

    def upload_text(self, *, object_key: str, text: str, content_type: str = "text/markdown; charset=utf-8") -> dict:
        return self.upload_bytes(
            filename=object_key.rsplit("/", 1)[-1],
            content_type=content_type,
            data=text.encode("utf-8"),
            object_key=object_key,
        )

    def download_bytes(self, object_key: str) -> bytes:
        settings = get_settings()
        if settings.storage.mode != "minio":
            raise AppError(status_code=400, code="INTERNAL_ERROR", message="当前仅实现 MinIO 下载")

        client = self._build_minio_client()
        bucket_name = settings.storage.minio.bucket_name
        response = client.get_object(bucket_name, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()


storage_service = StorageService()
