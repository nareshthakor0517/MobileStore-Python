# custom_filters.py
from django import template

register = template.Library()

@register.filter
def get_initials(user):
    """
    Returns initials from the user's full name or username.
    Priority: user.user_name > user.username > 'Anonymous'
    """
    if not user:
        return "A"  # Default initial for Anonymous

    # Try full name first
    name = getattr(user, 'user_name', None) or getattr(user, 'username', None) or "Anonymous"
    words = name.split()
    initials = "".join([w[0].upper() for w in words if w])
    return initials or "A"


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def mul(value, arg):
    # multiplication filter
    return float(value) * float(arg)

@register.filter
def div(value, arg):
    # division filter
    try:
        return float(value) / float(arg)
    except ZeroDivisionError:
        return 0

@register.filter
def split(value, sep):
    """Splits the string by separator."""
    return value.split(sep)

@register.filter
def to_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0
    
@register.filter
def multiply(value, arg):
    return value * arg

# Example: Round a float
@register.filter
def my_round(value, decimal_places=0):
    try:
        return round(float(value), int(decimal_places))
    except:
        return value
    
@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return float(value) - float(arg)
    except:
        return value


@register.filter(name='indian_format')
def indian_format(amount):
    """
    Converts a number (int or float) to Indian Rupee format (e.g., 1,23,456.78).
    """
    if amount is None or amount == 0:
        return "₹0"
    
    try:
        # Decimal ko float/string mein convert karna zaroori hai
        s = f"{float(amount):.2f}"
    except (TypeError, ValueError):
        # Agar invalid input ho
        return f"₹{amount}" 
        
    if '.' in s:
        main, decimal = s.split('.')
        if decimal == '00':
            decimal = None
    else:
        main, decimal = s, None
        
    main = main.lstrip('0') or '0'
    is_negative = main.startswith('-')
    if is_negative:
        main = main[1:]

    # --- Indian Format Logic ---
    if len(main) <= 3:
        formatted_main = main
    else:
        last_three = main[-3:]
        other_digits = main[:-3]
        formatted_other = ''
        
        while other_digits:
            chunk = other_digits[-2:]
            
            if formatted_other:
                formatted_other = chunk + ',' + formatted_other
            else:
                formatted_other = chunk
            
            other_digits = other_digits[:-2]

        formatted_main = f"{formatted_other},{last_three}"
        
    final_amount = formatted_main
    if decimal:
        final_amount = f"{final_amount}.{decimal}"
        
    if is_negative:
        return f"-₹{final_amount}"
    
    return f"₹{final_amount}"

# Agar aapke paas aur filters hain to unhe bhi is file mein add karein