from PIL import Image
from io import BytesIO


def compress_image(image_bytes):
    image_bytes.seek(0)
    with Image.open(image_bytes) as img:
        output_bytes = BytesIO()
        img.save(output_bytes, format="JPEG", optimize=True, quality=85)  # Adjust quality as needed
        output_bytes.seek(0)
    return output_bytes

