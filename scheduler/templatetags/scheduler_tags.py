"""
Custom template tags and filters for the scheduler app.

Provides utility filters for accessing dictionary items in templates.
"""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary by key in a template.
    
    Usage: {{ my_dict|get_item:key }}
    
    Args:
        dictionary: The dictionary to access
        key: The key to look up
        
    Returns:
        The value for the key, or None if not found
    """
    if dictionary is None:
        return None
    return dictionary.get(key)
