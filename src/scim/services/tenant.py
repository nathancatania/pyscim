from typing import Optional, List
from uuid import UUID
from tortoise.exceptions import DoesNotExist, IntegrityError

from ..models import Tenant
from ..utils import logger
from ..exceptions import ResourceNotFound, ResourceAlreadyExists, InvalidSyntax


class TenantService:
    """Service for managing tenants."""
    
    @staticmethod
    async def create_tenant(
        name: str,
        display_name: str,
        external_id: Optional[str] = None,
        settings: Optional[dict] = None,
        metadata: Optional[dict] = None
    ) -> Tenant:
        """
        Create a new tenant.
        
        Args:
            name: Unique identifier for the tenant (e.g., 'acme-corp')
            display_name: Human-readable name (e.g., 'Acme Corporation')
            external_id: Optional external system identifier
            settings: Optional tenant-specific settings
            metadata: Optional metadata
            
        Returns:
            The created tenant
            
        Raises:
            ResourceAlreadyExists: If tenant with same name or external_id already exists
            InvalidSyntax: If validation fails
        """
        try:
            tenant = await Tenant.create(
                name=name,
                display_name=display_name,
                external_id=external_id,
                settings=settings or {},
                metadata=metadata or {}
            )
            logger.info(f"Created tenant: {tenant.name} (ID: {tenant.id})")
            return tenant
        except IntegrityError as e:
            if "name" in str(e):
                raise ResourceAlreadyExists("Tenant", "name", name)
            elif "external_id" in str(e):
                raise ResourceAlreadyExists("Tenant", "external_id", external_id)
            else:
                raise InvalidSyntax(f"Failed to create tenant: {str(e)}")
    
    @staticmethod
    async def get_tenant(tenant_id: UUID) -> Tenant:
        """
        Get a tenant by ID.
        
        Args:
            tenant_id: The tenant UUID
            
        Returns:
            The tenant
            
        Raises:
            ResourceNotFound: If tenant not found
        """
        try:
            return await Tenant.get(id=tenant_id)
        except DoesNotExist:
            raise ResourceNotFound("Tenant", str(tenant_id))
    
    @staticmethod
    async def get_tenant_by_name(name: str) -> Tenant:
        """
        Get a tenant by name.
        
        Args:
            name: The tenant name
            
        Returns:
            The tenant
            
        Raises:
            ResourceNotFound: If tenant not found
        """
        tenant = await Tenant.filter(name=name).first()
        if not tenant:
            raise ResourceNotFound("Tenant", name)
        return tenant
    
    @staticmethod
    async def list_tenants(
        active_only: bool = True,
        offset: int = 0,
        limit: int = 100
    ) -> List[Tenant]:
        """
        List tenants.
        
        Args:
            active_only: Whether to only return active tenants
            offset: Pagination offset
            limit: Maximum number of results
            
        Returns:
            List of tenants
        """
        query = Tenant.all()
        if active_only:
            query = query.filter(active=True)
        
        return await query.offset(offset).limit(limit).order_by("name")
    
    @staticmethod
    async def update_tenant(
        tenant_id: UUID,
        display_name: Optional[str] = None,
        external_id: Optional[str] = None,
        active: Optional[bool] = None,
        settings: Optional[dict] = None,
        metadata: Optional[dict] = None
    ) -> Tenant:
        """
        Update a tenant.
        
        Args:
            tenant_id: The tenant UUID
            display_name: New display name
            external_id: New external ID
            active: Whether tenant is active
            settings: New settings (replaces existing)
            metadata: New metadata (replaces existing)
            
        Returns:
            The updated tenant
            
        Raises:
            ResourceNotFound: If tenant not found
            ResourceAlreadyExists: If update would cause a conflict
        """
        tenant = await TenantService.get_tenant(tenant_id)
        
        try:
            if display_name is not None:
                tenant.display_name = display_name
            if external_id is not None:
                tenant.external_id = external_id
            if active is not None:
                tenant.active = active
            if settings is not None:
                tenant.settings = settings
            if metadata is not None:
                tenant.metadata = metadata
            
            await tenant.save()
            logger.info(f"Updated tenant: {tenant.name} (ID: {tenant.id})")
            return tenant
            
        except IntegrityError as e:
            if "external_id" in str(e):
                raise ResourceAlreadyExists("Tenant", "external_id", external_id)
            else:
                raise InvalidSyntax(f"Failed to update tenant: {str(e)}")
    
    @staticmethod
    async def delete_tenant(tenant_id: UUID) -> None:
        """
        Delete a tenant.
        
        WARNING: This will cascade delete all associated data (users, groups, tokens, etc.)
        
        Args:
            tenant_id: The tenant UUID
            
        Raises:
            ResourceNotFound: If tenant not found
            InvalidSyntax: If deletion not allowed (e.g., default tenant)
        """
        # Prevent deletion of default tenant
        if str(tenant_id) == "00000000-0000-0000-0000-000000000001":
            raise InvalidSyntax("Cannot delete the default tenant")
        
        tenant = await TenantService.get_tenant(tenant_id)
        
        # Get counts for logging
        user_count = await tenant.users.all().count()
        group_count = await tenant.groups.all().count()
        token_count = await tenant.api_tokens.all().count()
        
        logger.warning(
            f"Deleting tenant '{tenant.name}' (ID: {tenant.id}) with "
            f"{user_count} users, {group_count} groups, {token_count} tokens"
        )
        
        await tenant.delete()
        logger.info(f"Deleted tenant: {tenant.name} (ID: {tenant_id})")
    
    @staticmethod
    async def get_or_create_default_tenant() -> Tenant:
        """
        Get or create the default tenant.
        
        Returns:
            The default tenant
        """
        default_tenant_id = "00000000-0000-0000-0000-000000000001"
        
        # Try to get existing default tenant
        try:
            return await TenantService.get_tenant(UUID(default_tenant_id))
        except ResourceNotFound:
            # Create default tenant
            logger.info("Creating default tenant")
            return await Tenant.create(
                id=default_tenant_id,
                name="default",
                display_name="Default Tenant",
                metadata={
                    "created_via": "auto_created",
                    "purpose": "default_tenant"
                }
            )
    
    @staticmethod
    async def get_tenant_stats(tenant_id: UUID) -> dict:
        """
        Get statistics for a tenant.
        
        Args:
            tenant_id: The tenant UUID
            
        Returns:
            Dictionary with tenant statistics
        """
        tenant = await TenantService.get_tenant(tenant_id)
        
        return {
            "id": str(tenant.id),
            "name": tenant.name,
            "display_name": tenant.display_name,
            "active": tenant.active,
            "created_at": tenant.created_at.isoformat(),
            "modified_at": tenant.modified_at.isoformat(),
            "counts": {
                "users": await tenant.users.all().count(),
                "groups": await tenant.groups.all().count(),
                "api_tokens": await tenant.api_tokens.all().count(),
            }
        }