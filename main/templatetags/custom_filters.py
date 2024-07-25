from django import template

register = template.Library()


@register.filter(name='is_number')
def is_number(value):
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False