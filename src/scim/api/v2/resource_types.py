from fastapi import APIRouter, Path
from scim.schemas import ListResponse, ErrorResponse
from scim.exceptions import ResourceNotFound
from typing import Dict, Any

router = APIRouter(tags=["ResourceTypes"])


# Define resource types
USER_RESOURCE_TYPE = {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
    "id": "User",
    "name": "User",
    "endpoint": "/Users",
    "description": "User Account",
    "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
    "schemaExtensions": [
        {
            "schema": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            "required": False
        }
    ],
    "meta": {
        "location": "/scim/v2/ResourceTypes/User",
        "resourceType": "ResourceType"
    }
}

GROUP_RESOURCE_TYPE = {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
    "id": "Group",
    "name": "Group",
    "endpoint": "/Groups",
    "description": "Group",
    "schema": "urn:ietf:params:scim:schemas:core:2.0:Group",
    "meta": {
        "location": "/scim/v2/ResourceTypes/Group",
        "resourceType": "ResourceType"
    }
}

RESOURCE_TYPES: Dict[str, Dict[str, Any]] = {
    "User": USER_RESOURCE_TYPE,
    "Group": GROUP_RESOURCE_TYPE
}


@router.get(
    "/ResourceTypes",
    response_model=ListResponse,
    response_model_exclude_none=True,
    name="List Resource Types"
)
async def list_resource_types() -> ListResponse:
    """List all supported resource types"""
    resources = list(RESOURCE_TYPES.values())
    
    return ListResponse(
        total_results=len(resources),
        Resources=resources,
        start_index=1,
        items_per_page=len(resources)
    )


@router.get(
    "/ResourceTypes/{resource_type_id}",
    response_model_exclude_none=True,
    responses={
        404: {"model": ErrorResponse, "description": "ResourceType not found"}
    },
    name="Get Resource Type"
)
async def get_resource_type(
    resource_type_id: str = Path(..., description="ResourceType ID")
) -> Dict[str, Any]:
    """Get a specific resource type by ID"""
    resource_type = RESOURCE_TYPES.get(resource_type_id)
    if not resource_type:
        raise ResourceNotFound("ResourceType", resource_type_id)
    
    return resource_type