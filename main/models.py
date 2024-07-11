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
    balance = models.DecimalField(max_digits=10, decimal_places=0)
    description = models.TextField(blank=True, null=True, max_length=255)
    isFavorite = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.name} ({self.account_type})"

    def get_transaction(self):
        return self.transaction_set.all()


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('payment', 'Payment'),
        ('transfer', 'Transfer')
    )
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=11, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=datetime.date.today)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} kr. on {self.date}"

    def save(self, *args, **kwargs):
        if self.pk is None:  # Only adjust balance for new transactions
            if self.transaction_type == 'indbetaling':
                self.account.balance += self.amount
            elif self.transaction_type == 'udgift':
                self.account.balance -= self.amount
            self.account.save()
        super().save(*args, **kwargs)