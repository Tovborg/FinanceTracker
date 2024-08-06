import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')  # Replace 'your_project' with your project name
django.setup()

from main.models import Paychecks  # Replace 'your_app' with the name of your app

# Fetch the paycheck you want to duplicate
original_paycheck = Paychecks.objects.first()  # Adjust the query as needed

if original_paycheck:
    for _ in range(20):
        # Duplicate the original paycheck instance
        new_paycheck = Paychecks(
            user=original_paycheck.user,
            amount=original_paycheck.amount,
            pay_date=original_paycheck.pay_date,
            pay_period_start=original_paycheck.pay_period_start,
            pay_period_end=original_paycheck.pay_period_end,
            employer=original_paycheck.employer,
            status=original_paycheck.status,
            description=original_paycheck.description,
        )
        # Save the new paycheck to the database
        new_paycheck.save()

    print('Successfully duplicated the paycheck 20 times')
else:
    print('No original paycheck found to duplicate')
