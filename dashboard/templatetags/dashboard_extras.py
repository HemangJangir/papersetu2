from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """Template filter to get dictionary value by key"""
    return dictionary.get(key)

@register.filter
def attr(obj, attr_name):
    """Template filter to get attribute by name."""
    return getattr(obj, attr_name, None)
