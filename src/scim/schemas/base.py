from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum


class SCIMSchemaUri(str, Enum):
    USER = "urn:ietf:params:scim:schemas:core:2.0:User"
    GROUP = "urn:ietf:params:scim:schemas:core:2.0:Group"
    ENTERPRISE_USER = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    LIST_RESPONSE = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
    ERROR = "urn:ietf:params:scim:api:messages:2.0:Error"
    PATCH_OP = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
    BULK_REQUEST = "urn:ietf:params:scim:api:messages:2.0:BulkRequest"
    BULK_RESPONSE = "urn:ietf:params:scim:api:messages:2.0:BulkResponse"


class ResourceType(str, Enum):
    USER = "User"
    GROUP = "Group"


class Meta(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    resource_type: ResourceType = Field(..., alias="resourceType")
    created: datetime
    last_modified: datetime = Field(..., alias="lastModified")
    location: Optional[str] = None
    version: Optional[str] = None


class MultiValuedAttribute(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    
    value: str
    display: Optional[str] = None
    type: Optional[str] = None
    primary: Optional[bool] = False


class Name(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    
    formatted: Optional[str] = None
    family_name: Optional[str] = Field(None, alias="familyName")
    given_name: Optional[str] = Field(None, alias="givenName")
    middle_name: Optional[str] = Field(None, alias="middleName")
    honorific_prefix: Optional[str] = Field(None, alias="honorificPrefix")
    honorific_suffix: Optional[str] = Field(None, alias="honorificSuffix")


class Address(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    
    formatted: Optional[str] = None
    street_address: Optional[str] = Field(None, alias="streetAddress")
    locality: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = Field(None, alias="postalCode")
    country: Optional[str] = None
    type: Optional[str] = None
    primary: Optional[bool] = False


class BaseResource(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    
    schemas: List[str]
    id: Optional[str] = None
    external_id: Optional[str] = Field(None, alias="externalId")
    meta: Optional[Meta] = None


class ListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    schemas: List[str] = [SCIMSchemaUri.LIST_RESPONSE.value]
    total_results: int = Field(..., alias="totalResults")
    Resources: List[Dict[str, Any]]
    start_index: int = Field(1, alias="startIndex")
    items_per_page: int = Field(..., alias="itemsPerPage")


class PatchOperation(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    
    op: str
    path: Optional[str] = None
    value: Optional[Union[str, int, bool, Dict[str, Any], List[Any]]] = None
    
    @field_validator("op")
    def validate_op(cls, v: str) -> str:
        allowed_ops = ["add", "remove", "replace"]
        if v.lower() not in allowed_ops:
            raise ValueError(f"Operation must be one of {allowed_ops}")
        return v.lower()


class PatchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    schemas: List[str] = [SCIMSchemaUri.PATCH_OP.value]
    Operations: List[PatchOperation]