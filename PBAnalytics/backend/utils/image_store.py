from io import BytesIO
from PIL import Image


def compress_image(image_bytes: bytes, max_size=(1280, 1280), quality: int = 78) -> tuple[bytes, str]:
    """
    Compresses image size for DB storage.
    Returns (compressed_bytes, content_type).
    Uses JPEG for storage efficiency.
    """
    with Image.open(BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        img.thumbnail(max_size)
        
        # Save the image to a BytesIO object with the specified quality
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True, progressive=True)
        return output.getvalue(), "image/jpeg"