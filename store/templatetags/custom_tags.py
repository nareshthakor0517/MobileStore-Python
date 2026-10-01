from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Return dictionary.get(key) safely from templates."""
    try:
        return dictionary.get(key)
    except Exception:
        return None

@register.filter
def percent(value, total):
    """Return integer percent of value/total (value and total expected numeric)."""
    try:
        v = float(value)
        t = float(total)
        if t == 0:
            return 0
        return int((v / t) * 100)
    except Exception:
        return 0
 