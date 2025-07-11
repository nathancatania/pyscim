from typing import Optional
from fastapi import HTTPException
from scim.schemas.error import ErrorResponse


class SCIMException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: Optional[str] = None,
        scim_type: Optional[str] = None,
    ):
        self.scim_type = scim_type
        super().__init__(
            status_code=status_code,
            detail=detail,
        )
    
    def to_error_response(self) -> ErrorResponse:
        return ErrorResponse(
            status=self.status_code,
            detail=self.detail,
            scim_type=self.scim_type
        )


class ResourceNotFound(SCIMException):
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            status_code=404,
            detail=f"{resource_type} with id '{resource_id}' not found",
        )


class ResourceAlreadyExists(SCIMException):
    def __init__(self, resource_type: str, attribute: str, value: str):
        super().__init__(
            status_code=409,
            detail=f"{resource_type} with {attribute} '{value}' already exists",
            scim_type="uniqueness"
        )


class InvalidSyntax(SCIMException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=400,
            detail=detail,
            scim_type="invalidSyntax"
        )


class InvalidFilter(SCIMException):
    def __init__(self, filter_expression: str, reason: str):
        super().__init__(
            status_code=400,
            detail=f"Invalid filter expression '{filter_expression}': {reason}",
            scim_type="invalidFilter"
        )


class InvalidPatch(SCIMException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=400,
            detail=detail,
            scim_type="invalidPath"
        )


class Unauthorized(SCIMException):
    def __init__(self, detail: str = "Invalid or missing authentication credentials"):
        super().__init__(
            status_code=401,
            detail=detail,
        )


class Forbidden(SCIMException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=403,
            detail=detail,
        )


class TooManyRequests(SCIMException):
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=429,
            detail=detail,
        )


class PreconditionFailed(SCIMException):
    def __init__(self, detail: str = "Resource version mismatch"):
        super().__init__(
            status_code=412,
            detail=detail,
        )