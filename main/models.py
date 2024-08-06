from django.db import models
from django.contrib.auth.models import User
import datetime
# Create your models here.

class Account(models.Model):
    ACCOUNT_TYPES = (
        ('savings', 'Savings'),
        ('checking', 'Checking'),
        ('Vacation', 'Vacation'),
        ('Retirement', 'Retirement'),
        ('Other', 'Other')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    account_type = models.CharField(max_length=50, choices=ACCOUNT_TYPES)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    balance = models.DecimalField(max_digits=10, decimal_places=0)
    description = models.TextField(blank=True, null=True, max_length=255)
    isFavorite = models.BooleanField(default=False)
    accumulated_interest = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.name} ({self.account_type})"

    def get_transactions(self):
        return self.transaction_set.all().order_by('-date')

    def get_three_recent_transactions(self):
        return self.transaction_set.all().order_by('-date')[:3]

    def get_monthly_expenses(self):
        today = datetime.date.today()
        first_day_of_month = today.replace(day=1)
        last_day_of_month = (today.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(
            days=1)

        transactions = self.transaction_set.filter(
            date__gte=first_day_of_month,
            date__lte=last_day_of_month,
            transaction_type__in=['withdrawal', 'payment']
        )

        total_expenses = sum(transaction.amount for transaction in transactions)
        return total_expenses

    def get_monthly_income(self):
        # Get the current date
        today = datetime.date.today()
        # Get the first and last day of the current month
        first_day_of_month = today.replace(day=1)
        last_day_of_month = (today.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(
            days=1)

        # Filter transactions for the current month
        transactions = self.transaction_set.filter(
            date__gte=first_day_of_month,
            date__lte=last_day_of_month,
            transaction_type='deposit'
        ).exclude(description__startswith='Transfer from')

        # Calculate the total income for the month
        total_income = sum(transaction.amount for transaction in transactions)

        return total_income


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('payment', 'Payment'),
        ('transfer', 'Transfer'),
    )
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=11, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=datetime.date.today)
    description = models.TextField(blank=True, null=True)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2, null=False, default=0) # Balance after transaction
    transfer_to = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transfer_to', null=True, blank=True)
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} kr. on {self.date}"


class Paychecks(models.Model):
    PAYCHECK_STATUS = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    pay_date = models.DateField(default=datetime.date.today)
    pay_period_start = models.DateField(default=datetime.date.today)
    pay_period_end = models.DateField(default=datetime.date.today)
    employer = models.CharField(max_length=50)
    status = models.CharField(max_length=50, choices=PAYCHECK_STATUS, default='pending')
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.employer} - {self.amount} kr. on {self.pay_date}"
