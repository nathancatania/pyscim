from typing import Optional
from fastapi import HTTPException, Request, status
from tortoise.exceptions import DoesNotExist

from ..models import Tenant


class TenantContext:
    """Manages tenant context for the current request."""
    
    def __init__(self, tenant: Tenant):
        self.tenant = tenant
        self.tenant_id = tenant.id
    
    @property
    def id(self) -> str:
        """Get the tenant ID."""
        return str(self.tenant_id)
    
    @property
    def name(self) -> str:
        """Get the tenant name."""
        return self.tenant.name
    
    @property
    def is_active(self) -> bool:
        """Check if the tenant is active."""
        return self.tenant.active


async def get_tenant_context(request: Request) -> TenantContext:
    """
    Extract tenant context from the request.
    
    The tenant is determined from the API token used for authentication.
    """
    # Check if authentication is present
    if not hasattr(request.state, "auth_user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Extract tenant_id from auth_user (set in auth middleware)
    tenant_id = getattr(request.state.auth_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant context not found in authentication"
        )
    
    # Load tenant from database
    try:
        tenant = await Tenant.get(id=tenant_id)
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tenant {tenant_id} not found"
        )
    
    # Check if tenant is active
    if not tenant.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is not active"
        )
    
    return TenantContext(tenant)


def apply_tenant_filter(query, tenant_context: TenantContext):
    """
    Apply tenant filtering to a Tortoise ORM query.
    
    Args:
        query: The base query to filter
        tenant_context: The current tenant context
        
    Returns:
        The filtered query
    """
    return query.filter(tenant_id=tenant_context.tenant_id)