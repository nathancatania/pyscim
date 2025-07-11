"""
SCIM Path Parser for RFC 7644 compliant path parsing.

Supports:
- Simple paths: "userName", "name.givenName"
- ValuePath with filters: "emails[type eq \"work\"].value"
- Complex filters: "members[value eq \"user-id\"]"
"""

import re
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class SCIMPath:
    """Represents a parsed SCIM path"""
    attribute: str  # Main attribute name (e.g., "emails", "name")
    filter_expr: Optional[str] = None  # Filter expression if present (e.g., 'type eq "work"')
    sub_attribute: Optional[str] = None  # Sub-attribute if present (e.g., "value", "givenName")
    schema_uri: Optional[str] = None  # Schema URI if fully qualified
    

def parse_scim_path(path: str) -> SCIMPath:
    """
    Parse a SCIM path according to RFC 7644.
    
    Examples:
        "userName" -> SCIMPath(attribute="userName")
        "name.givenName" -> SCIMPath(attribute="name", sub_attribute="givenName")
        "emails[type eq \"work\"].value" -> SCIMPath(attribute="emails", filter_expr='type eq "work"', sub_attribute="value")
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:manager" -> SCIMPath(schema_uri="...", attribute="manager")
    
    Args:
        path: The SCIM path to parse
        
    Returns:
        SCIMPath object with parsed components
        
    Raises:
        ValueError: If the path is invalid
    """
    if not path:
        raise ValueError("Path cannot be empty")
    
    # Check if it's a fully qualified path with schema URI
    schema_pattern = r'^(urn:[^:]+(?::[^:]+)*):([^.\[]+)(?:\.([^.\[]+))?$'
    schema_match = re.match(schema_pattern, path)
    if schema_match:
        schema_uri = schema_match.group(1)
        attribute = schema_match.group(2)
        sub_attribute = schema_match.group(3)
        return SCIMPath(
            attribute=attribute,
            sub_attribute=sub_attribute,
            schema_uri=schema_uri
        )
    
    # Pattern for paths with filters: attribute[filter].subAttribute or attribute[filter]
    filter_pattern = r'^([^.\[]+)\[([^\]]+)\](?:\.([^.\[]+))?$'
    filter_match = re.match(filter_pattern, path)
    if filter_match:
        attribute = filter_match.group(1)
        filter_expr = filter_match.group(2)
        sub_attribute = filter_match.group(3)
        return SCIMPath(
            attribute=attribute,
            filter_expr=filter_expr,
            sub_attribute=sub_attribute
        )
    
    # Pattern for simple paths: attribute.subAttribute or attribute
    simple_pattern = r'^([^.\[]+)(?:\.([^.\[]+))?$'
    simple_match = re.match(simple_pattern, path)
    if simple_match:
        attribute = simple_match.group(1)
        sub_attribute = simple_match.group(2)
        return SCIMPath(
            attribute=attribute,
            sub_attribute=sub_attribute
        )
    
    raise ValueError(f"Invalid SCIM path: {path}")


def parse_filter_expression(filter_expr: str) -> Dict[str, Any]:
    """
    Parse a filter expression like 'type eq "work"' or 'value eq "user-id"'.
    
    Returns:
        Dict with 'attribute', 'operator', and 'value' keys
    """
    # Simple parser for basic filter expressions
    # Supports: attribute op "value" or attribute op value
    pattern = r'^\s*(\w+)\s+(eq|ne|co|sw|ew|gt|ge|lt|le|pr)\s+("(?:[^"\\]|\\.)*"|\S+)\s*$'
    match = re.match(pattern, filter_expr, re.IGNORECASE)
    
    if not match:
        raise ValueError(f"Invalid filter expression: {filter_expr}")
    
    attribute = match.group(1)
    operator = match.group(2).lower()
    value = match.group(3)
    
    # Remove quotes if present
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1].replace('\\"', '"')
    
    return {
        "attribute": attribute,
        "operator": operator,
        "value": value
    }


def evaluate_filter(item: Dict[str, Any], filter_expr: str) -> bool:
    """
    Evaluate a filter expression against an item.
    
    Args:
        item: Dictionary representing the item to evaluate
        filter_expr: Filter expression like 'type eq "work"'
        
    Returns:
        True if the item matches the filter, False otherwise
    """
    try:
        filter_parts = parse_filter_expression(filter_expr)
        attribute = filter_parts["attribute"]
        operator = filter_parts["operator"]
        expected_value = filter_parts["value"]
        
        # Get the actual value from the item
        actual_value = item.get(attribute)
        if actual_value is None:
            return operator == "pr"  # "pr" (present) is false if attribute is missing
        
        # Convert to string for comparison
        actual_value = str(actual_value).lower()
        expected_value = str(expected_value).lower()
        
        # Evaluate based on operator
        if operator == "eq":
            return actual_value == expected_value
        elif operator == "ne":
            return actual_value != expected_value
        elif operator == "co":  # contains
            return expected_value in actual_value
        elif operator == "sw":  # starts with
            return actual_value.startswith(expected_value)
        elif operator == "ew":  # ends with
            return actual_value.endswith(expected_value)
        elif operator == "pr":  # present
            return True  # Already checked for None above
        else:
            # For gt, ge, lt, le - attempt numeric comparison
            try:
                actual_num = float(actual_value)
                expected_num = float(expected_value)
                if operator == "gt":
                    return actual_num > expected_num
                elif operator == "ge":
                    return actual_num >= expected_num
                elif operator == "lt":
                    return actual_num < expected_num
                elif operator == "le":
                    return actual_num <= expected_num
            except ValueError:
                # Fall back to string comparison
                if operator == "gt":
                    return actual_value > expected_value
                elif operator == "ge":
                    return actual_value >= expected_value
                elif operator == "lt":
                    return actual_value < expected_value
                elif operator == "le":
                    return actual_value <= expected_value
        
        return False
    except Exception:
        return False


def find_matching_items(items: list, filter_expr: str) -> list:
    """
    Find all items in a list that match a filter expression.
    
    Args:
        items: List of dictionaries to filter
        filter_expr: Filter expression like 'type eq "work"'
        
    Returns:
        List of matching items
    """
    return [item for item in items if evaluate_filter(item, filter_expr)]