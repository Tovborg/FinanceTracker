import os
import django

# Sæt Django settings-modulet
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_project.settings")
django.setup()  # Initialiser Django

# Importér først nu Django-modeller
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json

# Opret eller hent CrontabSchedule
schedule, created = CrontabSchedule.objects.get_or_create(
    minute="0",
    hour="0,13,20",  # Kører kl. 00:00, 13:00 og 20:00
    day_of_week="*",
    day_of_month="*",
    month_of_year="*",
    timezone="Europe/Copenhagen"
)

# Opret en PeriodicTask, hvis den ikke allerede findes
task, created = PeriodicTask.objects.get_or_create(
    crontab=schedule,
    name="Update OpenBanking Accounts",
    task="update_openbanking_accounts",  # Skift dette til din faktiske Celery-task
    defaults={"args": json.dumps([])},  # Tilføj eventuelle argumenter her
)

print("Celery Beat opgave oprettet eller opdateret!")