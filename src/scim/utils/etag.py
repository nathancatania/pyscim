import hashlib
import json
from typing import Any, Optional


def generate_etag(data: Any) -> str:
    if isinstance(data, dict):
        # Remove volatile fields
        data_copy = data.copy()
        data_copy.pop("meta", None)
        data_copy.pop("etag", None)
        json_str = json.dumps(data_copy, sort_keys=True, default=str)
    elif hasattr(data, "model_dump"):
        # Pydantic model
        json_str = json.dumps(data.model_dump(mode="json", exclude={"meta", "etag"}), sort_keys=True, default=str)
    else:
        json_str = str(data)
    
    return hashlib.md5(json_str.encode()).hexdigest()


def validate_etag(
    request_etag: Optional[str],
    resource_etag: Optional[str],
    if_match: bool = True
) -> bool:
    if not request_etag or not resource_etag:
        return True
    
    # Remove quotes if present
    request_etag = request_etag.strip('"')
    resource_etag = resource_etag.strip('"')
    
    if if_match:
        # If-Match: proceed only if ETags match
        return request_etag == resource_etag or request_etag == "*"
    else:
        # If-None-Match: proceed only if ETags don't match
        return request_etag != resource_etag and request_etag != "*"