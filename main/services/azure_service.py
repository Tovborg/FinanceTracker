import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, AnalyzeDocumentRequest
from django.conf import settings


def format_price(price_dict):
    return "".join([f"{p}" for p in price_dict.values()])


class AzureDocumentIntelligenceService:
    def __init__(self):
        self.client = DocumentIntelligenceClient(
            endpoint=settings.AZURE_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_KEY)
        )

    def analyze_receipts(self, image):
        path_to_sample_document = image
        with open(path_to_sample_document, "rb") as f:
            poller = self.client.begin_analyze_document(
                "prebuilt-receipt", analyze_request=f, locale="en-US", content_type="application/octet-stream"
            )
        receipts: AnalyzeResult = poller.result()
        analysis_results = []
        if receipts.documents:
            for idx, receipt in enumerate(receipts.documents):
                result = {
                    "receipt_number": idx + 1,
                    "doc_type": receipt.doc_type if receipt.doc_type else 'N/A',
                    "fields": {}
                }
                print(f"--------Analysis of receipt #{idx + 1}--------")
                print(f"Receipt type: {receipt.doc_type if receipt.doc_type else 'N/A'}")

                if receipt.fields:
                    merchant_name = receipt.fields.get("MerchantName")
                    if merchant_name:
                        result["fields"]["MerchantName"] = {
                            "valueString": merchant_name.get('valueString'),
                            "confidence": merchant_name.confidence
                        }
                        print(
                            f"Merchant Name: {merchant_name.get('valueString')} has confidence: "
                            f"{merchant_name.confidence}"
                        )
                    merchant_phone_number = receipt.fields.get("MerchantPhoneNumber")
                    print(merchant_phone_number)
                    if merchant_phone_number:
                        result["fields"]["MerchantPhoneNumber"] = {
                            "valuePhoneNumber": merchant_phone_number.get('content'),
                            "confidence": merchant_phone_number.confidence
                        }
                        print(
                            f"Merchant Phone Number: {merchant_phone_number.get('content')} has confidence: "
                            f"{merchant_phone_number.confidence}"
                        )
                    merchant_address = receipt.fields.get("MerchantAddress")
                    print(f"Merchant Address: {merchant_address}")
                    if merchant_address:
                        result["fields"]["MerchantAddress"] = {
                            "valueString": merchant_address.get('content'),
                            "valueAddress": merchant_address.get('valueAddress'),
                            "confidence": merchant_address.confidence
                        }
                        print(
                            f"Merchant Address: {merchant_address.get('content')} has confidence: "
                            f"{merchant_address.confidence}"
                        )

                    transaction_date = receipt.fields.get("TransactionDate")
                    print(f"Transaction Date: {transaction_date}")
                    if transaction_date:
                        if transaction_date.get('valueDate') is None:
                            result["fields"]["TransactionDate"] = {
                                "valueDate": transaction_date.get('content'),
                                "confidence": transaction_date.confidence
                            }
                        else:
                            result["fields"]["TransactionDate"] = {
                                "valueDate": transaction_date.get('valueDate'),
                                "confidence": transaction_date.confidence
                            }
                            print(
                                f"Transaction Date: {transaction_date.get('valueDate')} has confidence: "
                                f"{transaction_date.confidence}"
                            )
                    transaction_time = receipt.fields.get("TransactionTime")
                    print(f"Transaction Time: {transaction_time}")
                    if transaction_time:
                        result["fields"]["TransactionTime"] = {
                            "valueTime": transaction_time.get('valueTime'),
                            "confidence": transaction_time.confidence
                        }
                        print(
                            f"Transaction Time: {transaction_time.get('valueTime')} has confidence: "
                            f"{transaction_time.confidence}"
                        )
                    items = receipt.fields.get("Items")
                    if items:
                        result["fields"]["Items"] = []
                        print("Receipt items:")
                        for idx, item in enumerate(items.get("valueArray")):
                            item_data = {}

                            print(f"...Item #{idx + 1}")
                            item_description = item.get("valueObject").get("Description")
                            if item_description:
                                item_data["Description"] = {
                                    "valueString": item_description.get('valueString'),
                                    "confidence": item_description.confidence
                                }
                                print(
                                    f"......Item Description: {item_description.get('valueString')} has confidence: "
                                    f"{item_description.confidence}"
                                )
                            item_quantity = item.get("valueObject").get("Quantity")
                            print(f"item_quantity: {item_quantity}")
                            if item_quantity:
                                item_data["Quantity"] = {
                                    "valueNumber": item_quantity.get('valueNumber'),
                                    "confidence": item_quantity.confidence
                                }
                                print(
                                    f"......Item Quantity: {item_quantity.get('valueNumber')} has confidence: "
                                    f"{item_quantity.confidence}"
                                )
                            item_total_price = item.get("valueObject").get("TotalPrice")
                            if item_total_price:
                                item_data["TotalPrice"] = {
                                    "valueCurrency": item_total_price.get('valueCurrency'),
                                    "confidence": item_total_price.confidence
                                }
                                print(
                                    f"......Total Item Price: {format_price(item_total_price.get('valueCurrency'))} has confidence: "
                                    f"{item_total_price.confidence}"
                                )
                            result["fields"]["Items"].append(item_data)
                    subtotal = receipt.fields.get("Subtotal")
                    if subtotal:
                        result["fields"]["Subtotal"] = {
                            "valueCurrency": subtotal.get('valueCurrency'),
                            "confidence": subtotal.confidence
                        }
                        print(
                            f"Subtotal: {format_price(subtotal.get('valueCurrency'))} has confidence: {subtotal.confidence}"
                        )
                    tax = receipt.fields.get("TotalTax")
                    if tax:
                        result["fields"]["TotalTax"] = {
                            "valueCurrency": tax.get('valueCurrency'),
                            "confidence": tax.confidence
                        }
                        print(f"Total tax: {format_price(tax.get('valueCurrency'))} has confidence: {tax.confidence}")
                    tip = receipt.fields.get("Tip")
                    if tip:
                        result["fields"]["Tip"] = {
                            "valueCurrency": tip.get('valueCurrency'),
                            "confidence": tip.confidence
                        }
                        print(f"Tip: {format_price(tip.get('valueCurrency'))} has confidence: {tip.confidence}")
                    total = receipt.fields.get("Total")
                    if total:
                        result["fields"]["Total"] = {
                            "valueCurrency": total.get('valueCurrency'),
                            "confidence": total.confidence
                        }
                        print(f"Total: {format_price(total.get('valueCurrency'))} has confidence: {total.confidence}")
                print("--------------------------------------")
                analysis_results.append(result)
        return analysis_results

