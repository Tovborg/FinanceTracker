# Generated by Django 5.0.6 on 2024-07-12 10:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_transaction_balance_after'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='transfer_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transfer_to', to='main.account'),
        ),
    ]
