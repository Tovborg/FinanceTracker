from PIL import Image
from io import BytesIO
import json


def compress_image(image_bytes):
    image_bytes.seek(0)
    with Image.open(image_bytes) as img:
        output_bytes = BytesIO()
        img.save(output_bytes, format="JPEG", optimize=True, quality=85)  # Adjust quality as needed
        output_bytes.seek(0)
    return output_bytes


def serialize_analysis_results(results):
    if hasattr(results, 'to_dict'):
        return results.to_dict()

    return json.dumps(results, default=str)


def format_price(price_dict):
    return "".join([f"{p}" for p in price_dict.values()])


def clean_and_parse_json_string(json_string):
    """
    Clean and parse a JSON-like string with single quotes into a Python dictionary.
    """
    if not isinstance(json_string, str):
        return {}

    # Replace single quotes with double quotes for valid JSON
    json_string = json_string.replace("'", '"')

    try:
        # Load the string into a Python dictionary
        parsed_dict = json.loads(json_string)
    except json.JSONDecodeError:
        # Handle JSON decoding errors if any
        parsed_dict = {}

    return parsed_dict
