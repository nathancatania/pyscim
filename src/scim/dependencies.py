from typing import Optional, Annotated
from fastapi import Depends, Header, Query, Request
from scim.config import settings
from scim.utils import PaginationParams
from scim.utils.tenant_context import TenantContext, get_tenant_context
from scim.exceptions import Unauthorized


async def get_auth_token(authorization: Annotated[Optional[str], Header()] = None) -> str:
    if not settings.auth_enabled:
        return "bypass"

    if not authorization:
        raise Unauthorized("Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise Unauthorized("Invalid Authorization header format")

    return parts[1]


async def verify_token(token: Annotated[str, Depends(get_auth_token)]) -> dict:
    if not settings.auth_enabled:
        return {"sub": "anonymous", "role": "admin"}

    # Token verification is handled by the middleware
    # This dependency is kept for compatibility but
    # actual verification happens in AuthenticationMiddleware
    return {"sub": "api_token", "role": "scim_client"}


def get_pagination_params(
    start_index: Annotated[int, Query(alias="startIndex", ge=1)] = 1,
    count: Annotated[int, Query(ge=0, le=settings.max_page_size)] = settings.default_page_size,
) -> PaginationParams:
    return PaginationParams(start_index=start_index, count=count)


def get_attributes_params(
    attributes: Annotated[Optional[str], Query()] = None,
    excluded_attributes: Annotated[Optional[str], Query(alias="excludedAttributes")] = None,
) -> tuple[Optional[list[str]], Optional[list[str]]]:
    attrs = attributes.split(",") if attributes else None
    excluded = excluded_attributes.split(",") if excluded_attributes else None
    return attrs, excluded


def get_filter_param(filter: Annotated[Optional[str], Query()] = None) -> Optional[str]:
    return filter


def get_sort_params(
    sort_by: Annotated[Optional[str], Query(alias="sortBy")] = None,
    sort_order: Annotated[Optional[str], Query(alias="sortOrder")] = "ascending",
) -> tuple[Optional[str], str]:
    if sort_order not in ["ascending", "descending"]:
        sort_order = "ascending"
    return sort_by, sort_order


async def get_request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID", "unknown")


async def get_app_id(request: Request) -> str:
    """Extract app_id from authenticated request context."""
    if hasattr(request.state, "auth_user") and request.state.auth_user:
        app_id = request.state.auth_user.get("app_id")
        if not app_id:
            raise Unauthorized("No application context found")
        return app_id
    raise Unauthorized("Request not authenticated")


# Type aliases for dependency injection
AuthUser = Annotated[dict, Depends(verify_token)]
Pagination = Annotated[PaginationParams, Depends(get_pagination_params)]
AttributesFilter = Annotated[tuple[Optional[list[str]], Optional[list[str]]], Depends(get_attributes_params)]
FilterParam = Annotated[Optional[str], Depends(get_filter_param)]
SortParams = Annotated[tuple[Optional[str], str], Depends(get_sort_params)]
RequestId = Annotated[str, Depends(get_request_id)]
CurrentTenant = Annotated[TenantContext, Depends(get_tenant_context)]
AppId = Annotated[str, Depends(get_app_id)]
