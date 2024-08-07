import os


def format_price(price_dict):
    return "".join([f"{p}" for p in price_dict.values()])


def analyze_receipts():
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeResult, AnalyzeDocumentRequest

    # For how to obtain the endpoint and key, please see PREREQUISITES above.
    endpoint = os.environ["AZURE_ENDPOINT"]
    key = os.environ["AZURE_KEY"]

    document_intelligence_client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    # Analyze a document at a URL:
    # receiptUrl = "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/rest-api/receipt.png"
    # Replace with your actual receiptUrl:
    # If you use the URL of a public website, to find more URLs, please visit: https://aka.ms/more-URLs
    # If you analyze a document in Blob Storage, you need to generate Public SAS URL, please visit: https://aka.ms/create-sas-tokens
    # poller = document_intelligence_client.begin_analyze_document(
    #     "prebuilt-receipt",
    #     AnalyzeDocumentRequest(url_source=receiptUrl)
    # )

    # # If analyzing a local document, remove the comment markers (#) at the beginning of these 8 lines.
    # # Delete or comment out the part of "Analyze a document at a URL" above.
    # # Replace <path to your sample file>  with your actual file path.
    path_to_sample_document = "/Users/emiltovborg-jensen/Downloads/IMG_1613_11zon.JPG"
    with open(path_to_sample_document, "rb") as f:
        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-receipt", analyze_request=f, locale="en-US", content_type="application/octet-stream"
        )
    receipts: AnalyzeResult = poller.result()

    # [START analyze_receipts]
    if receipts.documents:
        for idx, receipt in enumerate(receipts.documents):
            print(f"--------Analysis of receipt #{idx + 1}--------")
            print(f"Receipt type: {receipt.doc_type if receipt.doc_type else 'N/A'}")
            if receipt.fields:
                merchant_name = receipt.fields.get("MerchantName")
                if merchant_name:
                    print(
                        f"Merchant Name: {merchant_name.get('valueString')} has confidence: "
                        f"{merchant_name.confidence}"
                    )
                transaction_date = receipt.fields.get("TransactionDate")
                if transaction_date:
                    print(
                        f"Transaction Date: {transaction_date.get('valueDate')} has confidence: "
                        f"{transaction_date.confidence}"
                    )
                items = receipt.fields.get("Items")
                if items:
                    print("Receipt items:")
                    for idx, item in enumerate(items.get("valueArray")):
                        print(f"...Item #{idx + 1}")
                        item_description = item.get("valueObject").get("Description")
                        if item_description:
                            print(
                                f"......Item Description: {item_description.get('valueString')} has confidence: "
                                f"{item_description.confidence}"
                            )
                        item_quantity = item.get("valueObject").get("Quantity")
                        if item_quantity:
                            print(
                                f"......Item Quantity: {item_quantity.get('valueString')} has confidence: "
                                f"{item_quantity.confidence}"
                            )
                        item_total_price = item.get("valueObject").get("TotalPrice")
                        if item_total_price:
                            print(
                                f"......Total Item Price: {format_price(item_total_price.get('valueCurrency'))} has confidence: "
                                f"{item_total_price.confidence}"
                            )
                subtotal = receipt.fields.get("Subtotal")
                if subtotal:
                    print(
                        f"Subtotal: {format_price(subtotal.get('valueCurrency'))} has confidence: {subtotal.confidence}"
                    )
                tax = receipt.fields.get("TotalTax")
                if tax:
                    print(f"Total tax: {format_price(tax.get('valueCurrency'))} has confidence: {tax.confidence}")
                tip = receipt.fields.get("Tip")
                if tip:
                    print(f"Tip: {format_price(tip.get('valueCurrency'))} has confidence: {tip.confidence}")
                total = receipt.fields.get("Total")
                if total:
                    print(f"Total: {format_price(total.get('valueCurrency'))} has confidence: {total.confidence}")
            print("--------------------------------------")
    # [END analyze_receipts]


if __name__ == "__main__":
    from azure.core.exceptions import HttpResponseError
    from dotenv import find_dotenv, load_dotenv

    try:
        load_dotenv(find_dotenv())
        analyze_receipts()
    except HttpResponseError as error:
        # Examples of how to check an HttpResponseError
        # Check by error code:
        if error.error is not None:
            if error.error.code == "InvalidImage":
                print(f"Received an invalid image error: {error.error}")
            if error.error.code == "InvalidRequest":
                print(f"Received an invalid request error: {error.error}")
            # Raise the error again after printing it
            raise
        # If the inner error is None and then it is possible to check the message to get more information:
        if "Invalid request".casefold() in error.message.casefold():
            print(f"Uh-oh! Seems there was an invalid request: {error}")
        # Raise the error again
        raise