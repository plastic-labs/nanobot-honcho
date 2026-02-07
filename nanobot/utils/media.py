"""Media file utilities."""

from pathlib import Path

from nanobot.utils.helpers import get_data_path, ensure_dir


# MIME type to file extension mapping
MIME_TYPE_EXTENSIONS: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/wav": ".wav",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}

# Media type to default extension mapping
MEDIA_TYPE_EXTENSIONS: dict[str, str] = {
    "image": ".jpg",
    "voice": ".ogg",
    "audio": ".mp3",
    "video": ".mp4",
    "file": "",
}


def get_media_path() -> Path:
    """Get the media directory for downloaded files."""
    return ensure_dir(get_data_path() / "media")


def get_extension(media_type: str, mime_type: str | None = None) -> str:
    """
    Get file extension from media type and optional MIME type.

    Args:
        media_type: General type (image, voice, audio, video, file).
        mime_type: Optional MIME type for more precise extension.

    Returns:
        File extension including the dot (e.g., ".jpg").
    """
    if mime_type and mime_type in MIME_TYPE_EXTENSIONS:
        return MIME_TYPE_EXTENSIONS[mime_type]
    return MEDIA_TYPE_EXTENSIONS.get(media_type, "")
