from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator
from .base import BaseResource, SCIMSchemaUri, Meta


class GroupMember(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    
    value: str
    ref: Optional[str] = Field(None, alias="$ref")
    display: Optional[str] = None
    type: Optional[str] = Field(default="User")


class Group(BaseResource):
    display_name: str = Field(..., alias="displayName")
    members: Optional[List[GroupMember]] = None
    
    @model_validator(mode="after")
    def set_default_schemas(self) -> "Group":
        self.schemas = [SCIMSchemaUri.GROUP.value]
        return self


class GroupRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    
    schemas: Optional[List[str]] = None
    display_name: str = Field(..., alias="displayName")
    external_id: Optional[str] = Field(None, alias="externalId")
    members: Optional[List[GroupMember]] = None


class GroupResponse(Group):
    id: str
    meta: Meta
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat() + "Z"
        }
    )