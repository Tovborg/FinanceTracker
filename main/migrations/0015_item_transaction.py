# Generated by Django 5.0.6 on 2024-08-09 15:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0014_item_transaction_merchant_address_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='transaction',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='main.transaction'),
        ),
    ]
