"""
SCIM Filter Parser - RFC 7644 Compliant

Implements SCIM filter parsing as defined in RFC 7644 Section 3.4.2.2
"""

import re
from typing import Any, List
from tortoise.expressions import Q


class SCIMFilterParser:
    """Parser for SCIM filter expressions to Tortoise ORM queries"""
    
    # Supported operators as per RFC 7644
    OPERATORS = {
        'eq': '__iexact',      # Equal (case-insensitive)
        'ne': '__not_iexact',  # Not equal (case-insensitive)
        'co': '__icontains',   # Contains (case-insensitive)
        'sw': '__istartswith', # Starts with (case-insensitive)
        'ew': '__iendswith',   # Ends with (case-insensitive)
        'pr': '__isnull',      # Present (has value)
        'gt': '__gt',          # Greater than
        'ge': '__gte',         # Greater than or equal
        'lt': '__lt',          # Less than
        'le': '__lte',         # Less than or equal
    }
    
    # Attribute mappings from SCIM to model fields
    USER_ATTRIBUTE_MAP = {
        'userName': 'user_name',
        'externalId': 'external_id',
        'displayName': 'display_name',
        'name.formatted': 'name_formatted',
        'name.familyName': 'name_family_name',
        'name.givenName': 'name_given_name',
        'name.middleName': 'name_middle_name',
        'active': 'active',
        'title': 'title',
        'userType': 'user_type',
        'preferredLanguage': 'preferred_language',
        'locale': 'locale',
        'timezone': 'timezone',
        'emails.value': 'emails__value',
        'emails.type': 'emails__type',
        'emails.primary': 'emails__primary_email',
        'phoneNumbers.value': 'phone_numbers__value',
        'phoneNumbers.type': 'phone_numbers__type',
        'addresses.locality': 'addresses__locality',
        'addresses.region': 'addresses__region',
        'addresses.country': 'addresses__country',
        'meta.created': 'created',
        'meta.lastModified': 'modified',
        'urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:employeeNumber': 'employee_number',
        'urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:department': 'department',
        'urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:organization': 'organization',
        'urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:division': 'division',
        'urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:costCenter': 'cost_center',
    }
    
    GROUP_ATTRIBUTE_MAP = {
        'displayName': 'display_name',
        'externalId': 'external_id',
        'members.value': 'members__user_id',
        'members.display': 'members__display',
        'meta.created': 'created',
        'meta.lastModified': 'modified',
    }
    
    def __init__(self, resource_type: str = 'User'):
        """Initialize parser for specific resource type"""
        self.resource_type = resource_type
        self.attribute_map = (
            self.USER_ATTRIBUTE_MAP if resource_type == 'User' 
            else self.GROUP_ATTRIBUTE_MAP
        )
    
    def parse(self, filter_string: str) -> Q:
        """
        Parse SCIM filter string to Tortoise Q object
        
        Args:
            filter_string: SCIM filter expression
            
        Returns:
            Tortoise Q object for filtering
            
        Raises:
            ValueError: If filter syntax is invalid
        """
        if not filter_string:
            return Q()
        
        # Remove extra whitespace
        filter_string = ' '.join(filter_string.split())
        
        # Handle logical operators
        if ' and ' in filter_string.lower():
            return self._parse_logical(filter_string, 'and')
        elif ' or ' in filter_string.lower():
            return self._parse_logical(filter_string, 'or')
        elif filter_string.lower().startswith('not '):
            return ~self.parse(filter_string[4:])
        
        # Handle parentheses
        if filter_string.startswith('(') and filter_string.endswith(')'):
            return self.parse(filter_string[1:-1])
        
        # Parse simple expression
        return self._parse_expression(filter_string)
    
    def _parse_logical(self, filter_string: str, operator: str) -> Q:
        """Parse logical operations (and/or)"""
        # Split by the operator, handling nested parentheses
        parts = self._split_logical(filter_string, operator)
        
        if len(parts) < 2:
            raise ValueError(f"Invalid {operator} expression")
        
        q_objects = [self.parse(part.strip()) for part in parts]
        
        if operator == 'and':
            result = q_objects[0]
            for q in q_objects[1:]:
                result &= q
            return result
        else:  # or
            result = q_objects[0]
            for q in q_objects[1:]:
                result |= q
            return result
    
    def _split_logical(self, filter_string: str, operator: str) -> List[str]:
        """Split filter string by logical operator, respecting parentheses"""
        parts = []
        current = []
        paren_depth = 0
        tokens = filter_string.split()
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            if token == '(':
                paren_depth += 1
            elif token == ')':
                paren_depth -= 1
            elif token.lower() == operator and paren_depth == 0:
                parts.append(' '.join(current))
                current = []
                i += 1
                continue
            
            current.append(token)
            i += 1
        
        if current:
            parts.append(' '.join(current))
        
        return parts
    
    def _parse_expression(self, expression: str) -> Q:
        """Parse a simple attribute operator value expression"""
        # Match: attribute operator "value" or attribute operator value
        pattern = r'^(\S+)\s+(eq|ne|co|sw|ew|pr|gt|ge|lt|le)\s*(.*)$'
        match = re.match(pattern, expression, re.IGNORECASE)
        
        if not match:
            raise ValueError(f"Invalid filter expression: {expression}")
        
        attr, op, value = match.groups()
        op = op.lower()
        
        # Get the mapped field name
        field = self.attribute_map.get(attr)
        if not field:
            # RFC 7644: Unsupported attributes should be ignored
            # Return empty Q that matches everything
            return Q()
        
        # Handle 'pr' (present) operator
        if op == 'pr':
            return Q(**{f"{field}__isnull": False})
        
        # Parse value
        value = self._parse_value(value)
        
        # Handle special cases for boolean fields
        if field in ['active', 'emails__primary_email']:
            if isinstance(value, str):
                value = value.lower() in ['true', '1', 'yes']
        
        # Build query
        if op == 'ne':
            # Not equal needs special handling
            return ~Q(**{f"{field}__iexact": value})
        else:
            suffix = self.OPERATORS.get(op, '__iexact')
            return Q(**{f"{field}{suffix}": value})
    
    def _parse_value(self, value: str) -> Any:
        """Parse value from filter string"""
        value = value.strip()
        
        # Remove quotes if present
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        
        # Try to parse as boolean
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        
        # Try to parse as number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        return value