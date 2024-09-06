from django import template

register = template.Library()


@register.filter(name='is_number')
def is_number(value):
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


@register.filter(name='translate_cardtype')
def translate_cardtype(value):
    if value == 'visa':
        return 'visa'
    elif value == 'dankort':
        return 'visa'
    elif value == 'mastercard':
        return 'mastercard'
    elif value == 'discover':
        return 'discover'
    elif value == 'american express':
        return 'amex'
    else:
        return 'credit card'
