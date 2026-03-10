import cloudinary
import cloudinary.uploader
from ..config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
)


def upload_avatar(file_bytes: bytes, public_id: str) -> str:
    """Upload avatar image to Cloudinary and return the secure URL."""
    result = cloudinary.uploader.upload(
        file_bytes,
        public_id=public_id,
        folder="nexabank/avatars",
        overwrite=True,
        resource_type="image",
        transformation=[
            {"width": 400, "height": 400, "crop": "fill", "gravity": "face"},
            {"quality": "auto", "fetch_format": "auto"},
        ],
    )
    return result["secure_url"]
