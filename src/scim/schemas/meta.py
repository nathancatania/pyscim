from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class AttributeType(str, Enum):
    STRING = "string"
    BOOLEAN = "boolean"
    DECIMAL = "decimal"
    INTEGER = "integer"
    DATETIME = "dateTime"
    REFERENCE = "reference"
    COMPLEX = "complex"


class Mutability(str, Enum):
    READ_ONLY = "readOnly"
    READ_WRITE = "readWrite"
    IMMUTABLE = "immutable"
    WRITE_ONLY = "writeOnly"


class Returned(str, Enum):
    ALWAYS = "always"
    NEVER = "never"
    DEFAULT = "default"
    REQUEST = "request"


class Uniqueness(str, Enum):
    NONE = "none"
    SERVER = "server"
    GLOBAL = "global"


class SchemaAttribute(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    name: str
    type: AttributeType
    multi_valued: bool = Field(False, alias="multiValued")
    description: Optional[str] = None
    required: bool = False
    canonical_values: Optional[List[str]] = Field(None, alias="canonicalValues")
    case_exact: bool = Field(False, alias="caseExact")
    mutability: Mutability = Mutability.READ_WRITE
    returned: Returned = Returned.DEFAULT
    uniqueness: Optional[Uniqueness] = Uniqueness.NONE
    sub_attributes: Optional[List["SchemaAttribute"]] = Field(None, alias="subAttributes")
    reference_types: Optional[List[str]] = Field(None, alias="referenceTypes")


class Schema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    attributes: List[SchemaAttribute]
    meta: Optional[Dict[str, Any]] = None


class ResourceType(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"]
    id: str
    name: str
    endpoint: str
    description: Optional[str] = None
    schema_uri: str = Field(..., alias="schema")
    schema_extensions: Optional[List[Dict[str, Any]]] = Field(None, alias="schemaExtensions")
    meta: Optional[Dict[str, Any]] = None


class ServiceProviderConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"]
    documentation_uri: Optional[str] = Field(None, alias="documentationUri")
    patch: Dict[str, bool]
    bulk: Dict[str, Any]
    filter: Dict[str, Any]
    change_password: Dict[str, bool] = Field(..., alias="changePassword")
    sort: Dict[str, bool]
    etag: Dict[str, bool]
    authentication_schemes: List[Dict[str, str]] = Field(..., alias="authenticationSchemes")
    meta: Optional[Dict[str, Any]] = None