import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def upload_avatar(file_bytes: bytes, filename: str, content_type: str) -> str:
    """
    Uploads an avatar to the Supabase Storage 'avatars' bucket (public).
    Returns the full public URL on success, or None on failure.
    """
    try:
        client = get_supabase_client()
        path = f"avatars/{filename}"
        client.storage.from_("avatars").upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        public_url = client.storage.from_("avatars").get_public_url(path)
        return public_url
    except Exception as e:
        logger.error(f"Avatar upload failed: {e}")
        return None
