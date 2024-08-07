from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Paychecks


class Command(BaseCommand):
    help = 'Update pending paychecks to paid if the payout date is today or earlier.'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        paychecks_to_update = Paychecks.objects.filter(status='pending', pay_date=today)

        for paycheck in paychecks_to_update:
            paycheck.status = 'paid'
            paycheck.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {paychecks_to_update.count()} paychecks'))
