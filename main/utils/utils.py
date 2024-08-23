from PIL import Image
from io import BytesIO
import json
import re
import os
from bs4 import BeautifulSoup
import requests
from main.models import Transaction
from django.conf import settings
import geoip2.database


def extract_amount(price_str):
    """
    Extracts the numeric amount from a price string.

    Args:
        price_str (str): The price string from which to extract the amount.

    Returns:
        float: The numeric amount extracted from the string, or 0.0 if extraction fails.
    """
    # Use regex to find all numeric parts in the string
    match = re.search(r'\d+(\.\d+)?', price_str)

    if match:
        return float(match.group())
    else:
        return 0.0


def extract_currency(price_str):
    """
    Extracts the currency code from a price string.

    Args:
        price_str (str): The price string from which to extract the currency code.

    Returns:
        str: The currency code extracted from the string, or an empty string if extraction fails.
    """
    # Use regex to find all alphabetic parts in the string (assuming currency code is at the end)
    match = re.search(r'[A-Za-z]+$', price_str)

    if match:
        return match.group()
    else:
        return "DKK"


def compress_image(image_bytes, max_size_mb=4):
    image_bytes.seek(0)
    with Image.open(image_bytes) as img:
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        output_bytes = BytesIO()
        img.save(output_bytes, format="JPEG", optimize=True, quality=85)  # Adjust quality as needed
        output_bytes.seek(0)

    compressed_size_kb = output_bytes.tell() / 1024

    if compressed_size_kb > max_size_mb * 1024:
        raise ValueError(f"Compressed image size exceeds {max_size_mb} MB limit")

    return output_bytes


def serialize_analysis_results(results):
    if hasattr(results, 'to_dict'):
        return results.to_dict()

    return json.dumps(results, default=str)


def format_price(price_dict):
    return "".join([f"{p}" for p in price_dict.values()])


def get_currency_code(price_dict, default="DKK"):
    return price_dict.get("currency", default)


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


# utils.py

def create_analysis_context(request, account, form, analysis_results):
    context = {
        "account": account,
        "form": form,
        "analysis_results": analysis_results,
        "merchant_name": "N/A",
        "merchant_phone_number": "N/A",
        "merchant_address": "N/A",
        "transaction_date": "N/A",
        "transaction_time": "N/A",
        "Items": [],
        "Subtotal": "N/A",
        "tax": "N/A",
        "tip": "N/A",
        "total": "N/A",
    }
    if isinstance(analysis_results, str):
        try:
            # Deserialize the JSON string back into a Python dictionary
            analysis_results = json.loads(analysis_results)
        except json.JSONDecodeError:
            # Handle JSON decoding errors if any
            analysis_results = None

    analysis_results = analysis_results[0]

    fields = analysis_results.get('fields')
    if analysis_results and isinstance(analysis_results, dict) and len(analysis_results) > 0:
        context['merchant_name'] = fields.get('MerchantName', {}).get('valueString', 'N/A')
        context['merchant_phone_number'] = fields.get('MerchantPhoneNumber', {}).get('content', 'N/A')
        if context['merchant_phone_number'] == 'N/A':
            context['merchant_phone_number'] = fields.get('MerchantPhoneNumber', {}).get('valuePhoneNumber', 'N/A')
        context['merchant_address'] = fields.get('MerchantAddress', {}).get('valueString', 'N/A')
        context['transaction_date'] = fields.get('TransactionDate', {}).get('valueDate', 'N/A')
        context['transaction_time'] = fields.get('TransactionTime', {}).get('valueTime', 'N/A')
        items = fields.get('Items', [])
        context['Items'] = [
            {
                'Description': item.get('Description', {}).get('valueString', 'N/A'),
                'Quantity': item.get('Quantity', {}).get('valueNumber', 1),
                'TotalPrice': clean_and_parse_json_string(item.get('TotalPrice', {}).get('valueCurrency', 'N/A')).get(
                    'amount', '0'),
            }
            for item in items
        ]

        context['Subtotal'] = extract_amount(
            format_price(clean_and_parse_json_string(fields.get('Subtotal', {}).get('valueCurrency', {}))))
        context['tax'] = extract_amount(
            format_price(clean_and_parse_json_string(fields.get('TotalTax', {}).get('valueCurrency', {}))))
        context['tip'] = extract_amount(
            format_price(clean_and_parse_json_string(fields.get('Tip', {}).get('valueCurrency', {}))))
        context['total'] = extract_amount(
            format_price(clean_and_parse_json_string(fields.get('Total', {}).get('valueCurrency', {}))))
        if context['Subtotal'] != 0.0:
            context['currency'] = extract_currency(
                format_price(clean_and_parse_json_string(fields.get('Subtotal', {}).get('valueCurrency', {}))))
        elif context['total'] != 0.0:
            context['currency'] = extract_currency(
                format_price(clean_and_parse_json_string(fields.get('Total', {}).get('valueCurrency', {}))))
        else:
            context['currency'] = 'DKK'

    return context


def get_payday_info():
    url = "https://xn--lnningsdag-0cb.dk/"
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad status codes

    soup = BeautifulSoup(response.content, 'html.parser')
    payday_span = soup.find('span', id='when')

    if payday_span:
        # only extract the number
        return payday_span.text.split()[1]
    else:
        return "Not available"


# Needs new logic to handle insufficient funds
def handleTransaction(transaction_type, amount, account, transaction, transfer_to=None):
    if transaction_type == 'deposit':
        account.balance += amount
    elif transaction_type == 'withdrawal':
        account.balance -= amount
    elif transaction_type == 'transfer' and transfer_to:
        account.balance -= amount
        transfer_to.balance += amount
        transfer_to.save()
        receiver_transaction = Transaction(
            account=transfer_to,
            transaction_type='deposit',
            amount=amount,
            date=transaction.date,
            description=f"Transfer from {account.name}",
            balance_after=transfer_to.balance
        )
        receiver_transaction.save()
    elif transaction_type == 'payment':
        account.balance -= amount
    elif transaction_type == 'purchase':
        account.balance -= amount
    elif transaction_type == 'wage deposit':
        account.balance += amount
    else:
        raise ValueError("Invalid transaction type")
    account.save()
    transaction.balance_after = account.balance
    transaction.save()


def get_client_ip(request):
    """
    Retrieve the client's IP address from the request object.
    :param request:
    :return: ip_address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_geoip_data(ip_address):
    geoip_city_db = os.path.join(settings.GEOIP_PATH, 'GeoLite2-City.mmdb')
    geoip_country_db = os.path.join(settings.GEOIP_PATH, 'GeoLite2-Country.mmdb')

    location_data = {}

    try:
        with geoip2.database.Reader(geoip_city_db) as city_reader:
            city_response = city_reader.city(ip_address)
            location_data['city'] = city_response.city.name
            location_data['country'] = city_response.country.name
            location_data['latitude'] = city_response.location.latitude
            location_data['longitude'] = city_response.location.longitude
    except geoip2.errors.AddressNotFoundError:
        location_data['city'] = None
        location_data['country'] = None
        location_data['latitude'] = None
        location_data['longitude'] = None

    return location_data

