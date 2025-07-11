from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from email_validator import validate_email
from ..utils.logging import logger
from .base import (
    BaseResource, 
    MultiValuedAttribute, 
    Name, 
    Address,
    SCIMSchemaUri,
    Meta
)


class Email(MultiValuedAttribute):
    @field_validator("value")
    def validate_email_format(cls, v: str) -> str:
        validate_email(v)
        return v.lower()


class Manager(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    
    value: Optional[str] = None
    ref: Optional[str] = Field(None, alias="$ref")
    display_name: Optional[str] = Field(None, alias="displayName")


class EnterpriseUserExtension(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    
    employee_number: Optional[str] = Field(None, alias="employeeNumber")
    cost_center: Optional[str] = Field(None, alias="costCenter")
    organization: Optional[str] = None
    division: Optional[str] = None
    department: Optional[str] = None
    manager: Optional[Union[str, Manager]] = None
    
    @field_validator("manager", mode="before")
    def normalize_manager(cls, v) -> Optional[Manager]:
        """Normalize manager field to always be a Manager object.
        
        This handles non-compliant SCIM implementations (like Entra ID) that
        send manager as a plain string instead of the complex object.
        """
        if v is None:
            return None
        elif isinstance(v, str):
            # Convert string to Manager object with just the value
            return Manager(value=v)
        elif isinstance(v, dict):
            # Let Pydantic handle dict conversion to Manager
            return v
        else:
            # Already a Manager object
            return v


class User(BaseResource):
    user_name: str = Field(..., alias="userName")
    name: Optional[Name] = None
    display_name: Optional[str] = Field(None, alias="displayName")
    nick_name: Optional[str] = Field(None, alias="nickName")
    profile_url: Optional[str] = Field(None, alias="profileUrl")
    title: Optional[str] = None
    user_type: Optional[str] = Field(None, alias="userType")
    preferred_language: Optional[str] = Field(None, alias="preferredLanguage")
    locale: Optional[str] = None
    timezone: Optional[str] = None
    active: bool = True
    password: Optional[str] = None
    
    emails: Optional[List[Email]] = None
    phone_numbers: Optional[List[MultiValuedAttribute]] = Field(None, alias="phoneNumbers")
    ims: Optional[List[MultiValuedAttribute]] = None
    photos: Optional[List[MultiValuedAttribute]] = None
    addresses: Optional[List[Address]] = None
    entitlements: Optional[List[MultiValuedAttribute]] = None
    roles: Optional[List[MultiValuedAttribute]] = None
    x509_certificates: Optional[List[MultiValuedAttribute]] = Field(None, alias="x509Certificates")
    
    # Extension schema
    urn_ietf_params_scim_schemas_extension_enterprise_2_0_User: Optional[EnterpriseUserExtension] = Field(
        None,
        alias="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )
    
    @field_validator("user_name")
    def validate_username(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("userName cannot be empty")
        return v.strip()
    
    @model_validator(mode="after")
    def set_default_schemas(self) -> "User":
        base_schemas = [SCIMSchemaUri.USER.value]
        
        # Add enterprise schema if extension is present
        if self.urn_ietf_params_scim_schemas_extension_enterprise_2_0_User:
            base_schemas.append(SCIMSchemaUri.ENTERPRISE_USER.value)
        
        self.schemas = base_schemas
        return self
    
    @model_validator(mode="after")
    def ensure_single_primary(self) -> "User":
        # Ensure only one primary email
        if self.emails:
            primary_count = sum(1 for email in self.emails if email.primary)
            if primary_count > 1:
                raise ValueError("Only one email can be marked as primary")
            elif primary_count == 0 and self.emails:
                self.emails[0].primary = True
        
        return self


class UserRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    
    schemas: Optional[List[str]] = None
    user_name: str = Field(..., alias="userName")
    name: Optional[Name] = None
    display_name: Optional[str] = Field(None, alias="displayName")
    nick_name: Optional[str] = Field(None, alias="nickName")
    profile_url: Optional[str] = Field(None, alias="profileUrl")
    title: Optional[str] = None
    user_type: Optional[str] = Field(None, alias="userType")
    preferred_language: Optional[str] = Field(None, alias="preferredLanguage")
    locale: Optional[str] = None
    timezone: Optional[str] = None
    active: bool = True
    password: Optional[str] = None
    external_id: Optional[str] = Field(None, alias="externalId")
    
    emails: Optional[List[Email]] = None
    phone_numbers: Optional[List[MultiValuedAttribute]] = Field(None, alias="phoneNumbers")
    ims: Optional[List[MultiValuedAttribute]] = None
    photos: Optional[List[MultiValuedAttribute]] = None
    addresses: Optional[List[Address]] = None
    entitlements: Optional[List[MultiValuedAttribute]] = None
    roles: Optional[List[MultiValuedAttribute]] = None
    x509_certificates: Optional[List[MultiValuedAttribute]] = Field(None, alias="x509Certificates")
    
    # Extension schema
    urn_ietf_params_scim_schemas_extension_enterprise_2_0_User: Optional[EnterpriseUserExtension] = Field(
        None,
        alias="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    )
    
    @model_validator(mode="before")
    def clean_empty_attributes(cls, values):
        """Remove empty objects from multi-valued attribute lists"""
        if isinstance(values, dict):
            # OneLogin compatibility: Handle non-standard enterprise extension key
            # OneLogin sends "urn:scim:schemas:extension:enterprise:2.0" instead of
            # the RFC-compliant "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
            onelogin_key = "urn:scim:schemas:extension:enterprise:2.0"
            standard_key = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
            
            if onelogin_key in values and standard_key not in values:
                logger.debug(f"Detected OneLogin non-standard enterprise extension key, converting to RFC-compliant format")
                values[standard_key] = values[onelogin_key]
                del values[onelogin_key]
            # Clean phone numbers
            if "phoneNumbers" in values and isinstance(values["phoneNumbers"], list):
                values["phoneNumbers"] = [
                    item for item in values["phoneNumbers"] 
                    if isinstance(item, dict) and item.get("value")
                ]
                if not values["phoneNumbers"]:
                    values["phoneNumbers"] = None
            
            # Clean addresses - keep if has any meaningful field
            if "addresses" in values and isinstance(values["addresses"], list):
                values["addresses"] = [
                    item for item in values["addresses"]
                    if isinstance(item, dict) and any(
                        item.get(field) for field in 
                        ["formatted", "streetAddress", "locality", "region", 
                         "postalCode", "country", "type", "primary"]
                    )
                ]
                if not values["addresses"]:
                    values["addresses"] = None
            
            # Clean other multi-valued attributes
            for field in ["ims", "photos", "entitlements", "roles", "x509Certificates"]:
                if field in values and isinstance(values[field], list):
                    values[field] = [
                        item for item in values[field]
                        if isinstance(item, dict) and item.get("value")
                    ]
                    if not values[field]:
                        values[field] = None
        
        return values


class UserGroup(BaseModel):
    """Represents a group membership for a user (read-only)"""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    
    value: str
    ref: Optional[str] = Field(None, alias="$ref")
    display: Optional[str] = None
    type: Optional[str] = Field(default="direct")


class UserResponse(User):
    id: str
    meta: Meta
    groups: Optional[List[UserGroup]] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat() + "Z"
        }
    )