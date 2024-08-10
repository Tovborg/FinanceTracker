# Generated by Django 5.0.6 on 2024-08-08 19:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_paychecks_payout_account'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='name',
            field=models.CharField(max_length=20),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='transaction_type',
            field=models.CharField(choices=[('deposit', 'Deposit'), ('withdrawal', 'Withdrawal'), ('payment', 'Payment'), ('transfer', 'Transfer'), ('purchase', 'Purchase')], max_length=11),
        ),
    ]