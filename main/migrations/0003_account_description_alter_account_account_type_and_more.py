# Generated by Django 5.0.6 on 2024-07-10 14:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_transaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='description',
            field=models.TextField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='account',
            name='account_type',
            field=models.CharField(choices=[('savings', 'Savings'), ('checking', 'Checking'), ('Vacation', 'Vacation'), ('Retirement', 'Retirement'), ('Other', 'Other')], max_length=50),
        ),
        migrations.AlterField(
            model_name='account',
            name='name',
            field=models.CharField(max_length=50),
        ),
    ]