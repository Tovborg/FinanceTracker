# Generated by Django 5.0.6 on 2024-09-04 14:40

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0019_userprofile"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="transaction_type",
            field=models.CharField(
                choices=[
                    ("deposit", "Deposit"),
                    ("withdrawal", "Withdrawal"),
                    ("payment", "Payment"),
                    ("transfer", "Transfer"),
                    ("purchase", "Purchase"),
                    ("wage deposit", "Wage Deposit"),
                    ("recurring", "Recurring"),
                ],
                max_length=12,
            ),
        ),
    ]
