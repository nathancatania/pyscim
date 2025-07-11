"""
SCIM Attribute Filtering Utility

Implements RFC 7644 Section 3.9 attribute filtering for SCIM responses.
Handles both 'attributes' and 'excludedAttributes' query parameters.
"""
from typing import Any, Dict, List, Optional, Set
from copy import deepcopy


class AttributeFilter:
    """Filters SCIM resource attributes according to RFC 7644."""
    
    # Attributes that MUST always be returned per RFC 7643
    ALWAYS_RETURNED = {
        "schemas",
        "id",
        "meta",
        "meta.resourceType",
        "meta.created",
        "meta.lastModified",
        "meta.location",
        "meta.version"
    }
    
    @classmethod
    def filter_resource(
        cls,
        resource: Dict[str, Any],
        attributes: Optional[List[str]] = None,
        excluded_attributes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Filter a single resource based on attributes/excludedAttributes parameters.
        
        Args:
            resource: The resource dictionary to filter
            attributes: List of attributes to include (overrides default set)
            excluded_attributes: List of attributes to exclude from default set
            
        Returns:
            Filtered resource dictionary
        """
        if not attributes and not excluded_attributes:
            return resource
            
        # Create a deep copy to avoid modifying the original
        filtered = deepcopy(resource)
        
        if attributes:
            # When attributes is specified, return minimum set + requested attributes
            return cls._apply_attributes_filter(filtered, attributes)
        elif excluded_attributes:
            # When excludedAttributes is specified, return default set minus excluded
            return cls._apply_excluded_attributes_filter(filtered, excluded_attributes)
            
        return filtered
    
    @classmethod
    def _apply_attributes_filter(
        cls,
        resource: Dict[str, Any],
        attributes: List[str]
    ) -> Dict[str, Any]:
        """Apply 'attributes' parameter filtering."""
        # Normalize attribute paths
        requested_attrs = cls._normalize_attribute_paths(attributes)
        
        # Always include minimum set
        attrs_to_keep = cls.ALWAYS_RETURNED.union(requested_attrs)
        
        # Filter the resource
        return cls._filter_dict(resource, attrs_to_keep, mode="include")
    
    @classmethod
    def _apply_excluded_attributes_filter(
        cls,
        resource: Dict[str, Any],
        excluded_attributes: List[str]
    ) -> Dict[str, Any]:
        """Apply 'excludedAttributes' parameter filtering."""
        # Normalize attribute paths
        excluded_attrs = cls._normalize_attribute_paths(excluded_attributes)
        
        # Never exclude always-returned attributes
        excluded_attrs = excluded_attrs - cls.ALWAYS_RETURNED
        
        # Filter the resource
        return cls._filter_dict(resource, excluded_attrs, mode="exclude")
    
    @classmethod
    def _normalize_attribute_paths(cls, attributes: List[str]) -> Set[str]:
        """
        Normalize attribute paths to handle case-insensitive matching
        and schema URN prefixes.
        
        Per RFC 7644 Section 3.10, attribute names are case-insensitive.
        """
        normalized = set()
        
        for attr in attributes:
            # Check if this is a URN-prefixed attribute
            if attr.startswith("urn:"):
                # For extension schemas, we need to preserve the URN
                # Format: urn:...:attributeName or urn:...:attributeName.subAttribute
                parts = attr.split(":")
                if len(parts) > 7:  # Has attribute after schema URN
                    # Get the schema URN (everything before the last colon)
                    schema_urn = ":".join(parts[:-1])
                    attribute_path = parts[-1]
                    # Add both the full path and the schema URN for matching
                    normalized.add(f"{schema_urn.lower()}:{attribute_path.lower()}")
                    normalized.add(schema_urn.lower())
                else:
                    # Just the schema URN itself
                    normalized.add(attr.lower())
            else:
                # Regular attribute without URN prefix
                normalized.add(attr.lower())
            
        return normalized
    
    @classmethod
    def _filter_dict(
        cls,
        data: Dict[str, Any],
        attribute_paths: Set[str],
        mode: str = "include",
        current_path: str = ""
    ) -> Dict[str, Any]:
        """
        Recursively filter a dictionary based on attribute paths.
        
        Args:
            data: Dictionary to filter
            attribute_paths: Set of normalized attribute paths
            mode: "include" to keep only specified paths, "exclude" to remove them
            current_path: Current path in the recursion (for nested attributes)
        """
        result = {}
        
        for key, value in data.items():
            # Build the full path for this attribute
            if current_path:
                full_path = f"{current_path}.{key}".lower()
            else:
                full_path = key.lower()
            
            # Check if this attribute should be included
            should_include = cls._should_include_attribute(
                full_path, attribute_paths, mode
            )
            
            if should_include:
                if isinstance(value, dict):
                    # Handle extension schemas specially
                    if key.startswith("urn:"):
                        # For extension schemas, we need to check if any attributes within it are requested
                        # Check if any attribute path starts with this URN
                        urn_has_attrs = any(
                            attr.startswith(f"{key.lower()}:") 
                            for attr in attribute_paths
                        )
                        if mode == "include" and urn_has_attrs:
                            # Filter the nested content with URN-prefixed paths
                            filtered_value = cls._filter_extension_schema(
                                value, attribute_paths, mode, key
                            )
                            if filtered_value:  # Only include if not empty
                                result[key] = filtered_value
                        elif mode == "exclude":
                            # For exclude mode, filter normally
                            filtered_value = cls._filter_dict(
                                value, attribute_paths, mode, full_path
                            )
                            if filtered_value:  # Only include if not empty
                                result[key] = filtered_value
                    else:
                        # Regular nested object
                        filtered_value = cls._filter_dict(
                            value, attribute_paths, mode, full_path
                        )
                        if filtered_value or full_path in cls.ALWAYS_RETURNED:
                            result[key] = filtered_value
                            
                elif isinstance(value, list):
                    # Handle multi-valued attributes
                    filtered_list = cls._filter_list(
                        value, attribute_paths, mode, full_path
                    )
                    if filtered_list is not None:
                        result[key] = filtered_list
                else:
                    # Simple value
                    result[key] = value
        
        return result
    
    @classmethod
    def _filter_list(
        cls,
        data: List[Any],
        attribute_paths: Set[str],
        mode: str,
        current_path: str
    ) -> Optional[List[Any]]:
        """Filter a list of values (multi-valued attributes)."""
        if not data:
            return data
            
        # For multi-valued attributes, check if any sub-attributes are requested
        result = []
        
        for item in data:
            if isinstance(item, dict):
                # Filter each object in the list
                filtered_item = cls._filter_dict(
                    item, attribute_paths, mode, current_path
                )
                if filtered_item:
                    result.append(filtered_item)
            else:
                # Simple values in list - include if parent path matches
                if cls._should_include_attribute(current_path, attribute_paths, mode):
                    result.append(item)
        
        return result if result else None
    
    @classmethod
    def _filter_extension_schema(
        cls,
        data: Dict[str, Any],
        attribute_paths: Set[str],
        mode: str,
        schema_urn: str
    ) -> Dict[str, Any]:
        """Filter extension schema attributes with URN-prefixed paths."""
        result = {}
        schema_urn_lower = schema_urn.lower()
        
        for key, value in data.items():
            # Build the URN-prefixed path for this attribute
            urn_path = f"{schema_urn_lower}:{key.lower()}"
            
            # Check if this specific extension attribute is requested
            should_include = False
            for attr_path in attribute_paths:
                if (attr_path == urn_path or
                    attr_path.startswith(f"{urn_path}.")):
                    should_include = True
                    break
            
            if should_include:
                if isinstance(value, dict):
                    # Nested object within extension
                    filtered_value = cls._filter_dict(
                        value, attribute_paths, mode, urn_path
                    )
                    if filtered_value:
                        result[key] = filtered_value
                elif isinstance(value, list):
                    # Multi-valued attribute within extension
                    filtered_list = cls._filter_list(
                        value, attribute_paths, mode, urn_path
                    )
                    if filtered_list is not None:
                        result[key] = filtered_list
                else:
                    # Simple value
                    result[key] = value
        
        return result
    
    @classmethod
    def _should_include_attribute(
        cls,
        path: str,
        attribute_paths: Set[str],
        mode: str
    ) -> bool:
        """
        Determine if an attribute should be included based on the filter mode.
        
        Handles both exact matches and parent path matches for nested attributes.
        """
        path_lower = path.lower()
        
        # Always include minimum required attributes
        if path_lower in cls.ALWAYS_RETURNED:
            return True
        
        if mode == "include":
            # Include if path matches or is a parent of a requested path
            for attr_path in attribute_paths:
                if (path_lower == attr_path or 
                    attr_path.startswith(f"{path_lower}.") or
                    path_lower.startswith(f"{attr_path}.")):
                    return True
            return False
        else:  # mode == "exclude"
            # Exclude if path matches exactly or is a child of excluded path
            for attr_path in attribute_paths:
                if (path_lower == attr_path or 
                    path_lower.startswith(f"{attr_path}.")):
                    return False
            return True
    
    @classmethod
    def filter_list_response(
        cls,
        resources: List[Dict[str, Any]],
        attributes: Optional[List[str]] = None,
        excluded_attributes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter multiple resources in a list response.
        
        Args:
            resources: List of resource dictionaries
            attributes: Attributes to include
            excluded_attributes: Attributes to exclude
            
        Returns:
            List of filtered resources
        """
        if not attributes and not excluded_attributes:
            return resources
            
        return [
            cls.filter_resource(resource, attributes, excluded_attributes)
            for resource in resources
        ]