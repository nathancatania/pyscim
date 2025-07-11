from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator
from .base import SCIMSchemaUri


class BulkOperation(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    
    method: str
    path: str
    bulk_id: Optional[str] = Field(None, alias="bulkId")
    version: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
    @field_validator("method")
    def validate_method(cls, v: str) -> str:
        allowed_methods = ["POST", "PUT", "PATCH", "DELETE"]
        if v.upper() not in allowed_methods:
            raise ValueError(f"Method must be one of {allowed_methods}")
        return v.upper()


class BulkRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    schemas: List[str] = [SCIMSchemaUri.BULK_REQUEST.value]
    fail_on_errors: Optional[int] = Field(None, alias="failOnErrors")
    Operations: List[BulkOperation]


class BulkResponseOperation(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    
    method: str
    location: Optional[str] = None
    bulk_id: Optional[str] = Field(None, alias="bulkId")
    version: Optional[str] = None
    status: Union[str, int]
    response: Optional[Dict[str, Any]] = None


class BulkResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    schemas: List[str] = [SCIMSchemaUri.BULK_RESPONSE.value]
    Operations: List[BulkResponseOperation]