# src/utils/parsers.py
import json
import re

def parse_json(json_string: str):
    """Robustly parse a JSON string that might be embedded in other text."""
    # Find the start of the JSON array or object
    json_start = -1
    for i, char in enumerate(json_string):
        if char in ('{', '['):
            json_start = i
            break

    if json_start == -1:
        raise json.JSONDecodeError("No JSON object or array found in the string.", json_string, 0)

    # Find the end of the JSON array or object
    json_end = -1
    if json_string[json_start] == '[':
        end_char = ']'
    else:
        end_char = '}'
    
    open_brackets = 0
    for i, char in enumerate(json_string[json_start:]):
        if char == json_string[json_start]:
            open_brackets += 1
        elif char == end_char:
            open_brackets -= 1
            if open_brackets == 0:
                json_end = json_start + i + 1
                break

    if json_end == -1:
        raise json.JSONDecodeError("Could not find matching end bracket for JSON object.", json_string, 0)

    json_str = json_string[json_start:json_end]
    return json.loads(json_str)
