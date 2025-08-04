"""Storage service for file uploads and management."""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
import aiofiles
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageService:
    """Service for managing file storage."""

    def __init__(self):
        # In production, this would use Google Cloud Storage
        # For now, using local file storage
        self.base_path = Path(os.getenv("STORAGE_PATH", "/tmp/luckygas-storage"))
        self.base_url = os.getenv("STORAGE_BASE_URL", "http://localhost:8000/files")

        # Create base directory if it doesn't exist
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload_file(
        self, file_path: str, destination_path: str, public: bool = False
    ) -> str:
        """Upload a file and return its URL."""
        try:
            # Generate unique filename
            file_id = str(uuid.uuid4())
            original_name = os.path.basename(file_path)
            extension = os.path.splitext(original_name)[1]
            unique_name = f"{file_id}{extension}"

            # Create destination directory
            dest_dir = self.base_path / destination_path
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Copy file to destination
            dest_file = dest_dir / unique_name

            async with aiofiles.open(file_path, "rb") as src:
                content = await src.read()

            async with aiofiles.open(dest_file, "wb") as dst:
                await dst.write(content)

            # Generate URL
            relative_path = f"{destination_path}/{unique_name}"
            url = f"{self.base_url}/{relative_path}"

            logger.info(f"File uploaded successfully: {url}")
            return url

        except Exception as e:
            logger.error(f"Failed to upload file: {str(e)}")
            raise

    async def delete_file(self, file_url: str) -> bool:
        """Delete a file by its URL."""
        try:
            # Extract relative path from URL
            if file_url.startswith(self.base_url):
                relative_path = file_url[len(self.base_url) + 1 :]
                file_path = self.base_path / relative_path

                if file_path.exists():
                    os.remove(file_path)
                    logger.info(f"File deleted: {file_url}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            return False

    async def get_signed_url(self, file_url: str, expiration_minutes: int = 60) -> str:
        """Get a signed URL for temporary access."""
        # In production, this would use Google Cloud Storage signed URLs
        # For now, just return the original URL with a timestamp
        timestamp = int(
            (datetime.now() + timedelta(minutes=expiration_minutes)).timestamp()
        )
        return f"{file_url}?expires={timestamp}"

    def get_file_path(self, file_url: str) -> Optional[Path]:
        """Get the local file path from a URL."""
        if file_url.startswith(self.base_url):
            relative_path = file_url[len(self.base_url) + 1 :]
            file_path = self.base_path / relative_path

            if file_path.exists():
                return file_path

        return None
