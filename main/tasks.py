from celery import shared_task
from django.db import transaction
from .models import OpenBankingAccount, OpenBankingTransaction, User
from .services.nordigen_services import OpenBankingService

@shared_task
def update_openbanking_accounts():
    """
    This task updates all OpenBankingAccount objects in the database.
    Runs at:
    
    """
    accounts_scraped = []
    accounts_skipped = []

    # Group accounts by user to avoid multiple session initializations
    users = OpenBankingAccount.objects.values_list("user", flat=True).distinct()

    for user_id in users:
        user = User.objects.get(id=user_id)

        try:
            print(f"🔄 Initializing OpenBankingService for user {user}")
            service = OpenBankingService(user)  # Create one session per user

            for account in OpenBankingAccount.objects.filter(user=user):
                print(f"🔄 Updating account {account.name} (ID: {account.account_id}) for user {user}")

                account_api = service.client.account_api(id=account.account_id)

                # Fetch data (handling rate limits)
                try:
                    account_details = account_api.get_details()
                    account_balances = account_api.get_balances()
                    account_transactions = account_api.get_transactions()
                except Exception as e:
                    print(f"❌ Failed to fetch data for account {account.account_id}: {e}")
                    accounts_skipped.append(account.account_id)
                    continue  # Move to the next account

                # Start atomic transaction
                with transaction.atomic():
                    # Update account balance
                    balance = (
                        account_balances.get("balances", [{}])[0]
                        .get("balanceAmount", {})
                        .get("amount", account.balance)
                    )
                    account.balance = balance
                    account.save()

                    print(f"✅ Updated OpenBankingAccount: {account.name} (Balance: {account.balance})")

                    # Process transactions
                    booked_transactions = account_transactions.get("transactions", {}).get("booked", [])
                    new_transactions = []

                    for tx in booked_transactions:
                        transaction_id = tx.get("transactionId")
                        if OpenBankingTransaction.objects.filter(transaction_id=transaction_id, account=account).exists():
                            continue  # Skip existing transactions

                        amount = float(tx.get("transactionAmount", {}).get("amount", "0.00"))
                        currency = tx.get("transactionAmount", {}).get("currency", "DKK")
                        booking_date = tx.get("bookingDate", "0000-00-00")

                        # Extract description safely
                        description = tx.get("remittanceInformationUnstructuredArray", [])
                        if description:
                            description = description[0]
                        else:
                            description = tx.get("remittanceInformationUnstructured", "") or ""

                        # If multiple lines, take the first line
                        description = description.split("\n")[0]

                        new_transactions.append(
                            OpenBankingTransaction(
                                account=account,
                                transaction_id=transaction_id,
                                amount=amount,
                                currency=currency,
                                date=booking_date,
                                description=description,
                            )
                        )

                    # Bulk insert transactions for efficiency
                    OpenBankingTransaction.objects.bulk_create(new_transactions)
                    print(f"✅ Inserted {len(new_transactions)} new transactions for {account.name}")

                accounts_scraped.append(account.account_id)

        except Exception as e:
            print(f"❌ Error updating accounts for user {user}: {e}")

    return {"updated_accounts": accounts_scraped, "skipped_accounts": accounts_skipped}