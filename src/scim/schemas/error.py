from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from .base import SCIMSchemaUri


class ErrorDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    
    scim_type: Optional[str] = Field(None, alias="scimType")
    detail: Optional[str] = None
    status: int


class ErrorResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    schemas: List[str] = [SCIMSchemaUri.ERROR.value]
    detail: Optional[str] = None
    status: int
    scim_type: Optional[str] = Field(None, alias="scimType")


class SCIMError(Exception):
    def __init__(
        self,
        status: int,
        detail: Optional[str] = None,
        scim_type: Optional[str] = None
    ):
        self.status = status
        self.detail = detail
        self.scim_type = scim_type
        super().__init__(detail or f"SCIM Error: {status}")