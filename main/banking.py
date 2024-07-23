import calendar
from datetime import datetime, timedelta


def get_last_banking_day(year, month):
    # Find the last day of the month
    last_day = calendar.monthrange(year, month)[1]

    # Create a date object for the last day of the month
    last_date = datetime(year, month, last_day)

    # If the last day is a weekend, find the previous Friday
    if last_date.weekday() >= 5:  # Saturday or Sunday
        last_date -= timedelta(days=last_date.weekday() - 4)  # Adjust to the previous Friday

    return last_date


def time_until_last_banking_day():
    today = datetime.now()
    last_banking_day = get_last_banking_day(today.year, today.month)

    if today > last_banking_day:
        # If today's date is past the last banking day, calculate for the next month
        if today.month == 12:
            next_year = today.year + 1
            next_month = 1
        else:
            next_year = today.year
            next_month = today.month + 1

        last_banking_day = get_last_banking_day(next_year, next_month)

    # Calculate the difference between today and the last banking day
    delta = last_banking_day - today

    return delta


# Print the time until the last banking day
delta = time_until_last_banking_day()
print(f"Time until the last banking day of the month: {delta.days} days and {delta.seconds // 3600} hours")
