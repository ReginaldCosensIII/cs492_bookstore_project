# cs492_bookstore_project/app/utils.py
from markupsafe import escape as markupsafe_escape 
import re

DEFAULT_LOWERCASE_FIELDS = {'email', 'username'}

def sanitize_html_text(text_input):
    """
    Sanitizes a single string input by stripping whitespace and then escaping HTML characters.
    """
    if not isinstance(text_input, str):
        return text_input
    return markupsafe_escape(text_input.strip())


def sanitize_form_field_value(value, key_name=None, lowercase_fields_set=None, should_escape_html=True): # CHANGED HERE
    """
    Sanitizes a single form field value.
    - Strips whitespace if it's a string.
    - Converts to lowercase if it's a string and key_name is in lowercase_fields_set.
    - HTML-escapes the string if should_escape_html is True.
    """
    if lowercase_fields_set is None:
        lowercase_fields_set = DEFAULT_LOWERCASE_FIELDS

    if isinstance(value, str):
        processed_value = value.strip()
        if key_name and key_name in lowercase_fields_set:
            processed_value = processed_value.lower()
        
        if should_escape_html: # CHANGED HERE
            processed_value = markupsafe_escape(processed_value)
        return processed_value
    return value


def sanitize_form_data(form_data_dict, lowercase_fields_set=None, escape_html_fields=None):
    """
    Sanitizes string values within a dictionary (typically from flat form data).
    """
    if not isinstance(form_data_dict, dict):
        return form_data_dict 

    if lowercase_fields_set is None:
        lowercase_fields_set = DEFAULT_LOWERCASE_FIELDS
    if escape_html_fields is None:
        escape_html_fields = set() 
    
    sanitized_data = {}
    for key, value in form_data_dict.items():
        should_escape = key in escape_html_fields
        sanitized_data[key] = sanitize_form_field_value(
            value, 
            key_name=key, 
            lowercase_fields_set=lowercase_fields_set, 
            should_escape_html=should_escape # This call is now correct
        )
    return sanitized_data

def normalize_whitespace(text):
    """
    Normalizes all whitespace in a string.
    """
    if not isinstance(text, str):
        return text
    normalized_text = re.sub(r'\s+', ' ', text)
    return normalized_text.strip()