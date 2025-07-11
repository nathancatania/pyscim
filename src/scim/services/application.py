from typing import List, Optional
from uuid import UUID
from tortoise.exceptions import IntegrityError, DoesNotExist
from scim.models import Application, Tenant
from scim.exceptions import ResourceNotFound, ResourceAlreadyExists
from scim.utils import logger


class ApplicationService:
    @staticmethod
    async def create_application(
        tenant_id: str,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        external_id: Optional[str] = None,
        settings: Optional[dict] = None,
        metadata: Optional[dict] = None
    ) -> Application:
        """Create a new application within a tenant."""
        try:
            # Verify tenant exists
            tenant = await Tenant.filter(id=tenant_id).first()
            if not tenant:
                raise ResourceNotFound("Tenant", tenant_id)
            
            # Create application
            app = await Application.create(
                tenant_id=tenant_id,
                name=name,
                display_name=display_name,
                description=description,
                external_id=external_id,
                settings=settings or {},
                metadata=metadata or {}
            )
            
            logger.info(f"Created application '{name}' (ID: {app.id}) for tenant {tenant_id}")
            return app
            
        except IntegrityError as e:
            if "name" in str(e):
                raise ResourceAlreadyExists("Application", "name", name)
            elif "external_id" in str(e):
                raise ResourceAlreadyExists("Application", "externalId", external_id)
            raise
    
    @staticmethod
    async def get_application(app_id: str) -> Application:
        """Get an application by ID."""
        app = await Application.filter(id=app_id).prefetch_related("tenant").first()
        
        if not app:
            raise ResourceNotFound("Application", app_id)
        
        return app
    
    @staticmethod
    async def get_application_by_name(tenant_id: str, name: str) -> Application:
        """Get an application by name within a tenant."""
        app = await Application.filter(
            tenant_id=tenant_id,
            name=name
        ).prefetch_related("tenant").first()
        
        if not app:
            raise ResourceNotFound("Application", f"{name} in tenant {tenant_id}")
        
        return app
    
    @staticmethod
    async def get_application_by_name_case_insensitive(tenant_id: Optional[str], name: str) -> Optional[Application]:
        """Get an application by name (case-insensitive) within a tenant or across all tenants."""
        query = Application.filter(name__iexact=name)
        
        if tenant_id:
            query = query.filter(tenant_id=tenant_id)
        
        return await query.prefetch_related("tenant").first()
    
    @staticmethod
    async def list_applications(
        tenant_id: Optional[str] = None,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 100
    ) -> tuple[List[Application], int]:
        """List applications with optional filtering."""
        query = Application.all()
        
        if tenant_id:
            query = query.filter(tenant_id=tenant_id)
        
        if active_only:
            query = query.filter(active=True)
        
        # Get total count
        total_count = await query.count()
        
        # Apply pagination
        apps = await query.offset(offset).limit(limit).prefetch_related("tenant").order_by("created_at")
        
        return apps, total_count
    
    @staticmethod
    async def update_application(
        app_id: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        external_id: Optional[str] = None,
        active: Optional[bool] = None,
        settings: Optional[dict] = None,
        metadata: Optional[dict] = None
    ) -> Application:
        """Update an application's properties."""
        app = await ApplicationService.get_application(app_id)
        
        # Update fields if provided
        if display_name is not None:
            app.display_name = display_name
        if description is not None:
            app.description = description
        if external_id is not None:
            app.external_id = external_id
        if active is not None:
            app.active = active
        if settings is not None:
            app.settings = settings
        if metadata is not None:
            app.metadata = metadata
        
        try:
            await app.save()
            logger.info(f"Updated application {app_id}")
            return app
        except IntegrityError as e:
            if "external_id" in str(e):
                raise ResourceAlreadyExists("Application", "externalId", external_id)
            raise
    
    @staticmethod
    async def delete_application(app_id: str) -> None:
        """Delete an application and all associated resources."""
        app = await ApplicationService.get_application(app_id)
        
        # Log warning about cascade deletion
        logger.warning(
            f"Deleting application '{app.name}' (ID: {app_id}) will cascade delete all associated "
            f"API tokens, users, groups, and audit logs."
        )
        
        await app.delete()
        logger.info(f"Deleted application {app_id}")
    
    @staticmethod
    async def deactivate_application(app_id: str) -> Application:
        """Deactivate an application without deleting it."""
        app = await ApplicationService.get_application(app_id)
        app.active = False
        await app.save()
        
        logger.info(f"Deactivated application {app_id}")
        return app
    
    @staticmethod
    async def get_application_stats(app_id: str) -> dict:
        """Get statistics about an application's resources."""
        app = await ApplicationService.get_application(app_id)
        
        # Import here to avoid circular imports
        from scim.models import User, Group, APIToken, AuditLog
        
        stats = {
            "id": str(app.id),
            "name": app.name,
            "display_name": app.display_name,
            "active": app.active,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "users_count": await User.filter(app_id=app_id).count(),
            "groups_count": await Group.filter(app_id=app_id).count(),
            "api_tokens_count": await APIToken.filter(app_id=app_id).count(),
            "active_tokens_count": await APIToken.filter(app_id=app_id, active=True).count(),
            "recent_activity_count": await AuditLog.filter(app_id=app_id).count(),
        }
        
        return stats
    
    @staticmethod
    async def get_or_create_default_application(tenant_id: str) -> Application:
        """Get or create a default application for a tenant."""
        # Try to get existing default app
        default_app = await Application.filter(
            tenant_id=tenant_id,
            name="default"
        ).first()
        
        if not default_app:
            # Create default application
            default_app = await ApplicationService.create_application(
                tenant_id=tenant_id,
                name="default",
                display_name="Default Application",
                description="Default application for single-IdP deployments",
                metadata={
                    "created_via": "auto_created",
                    "purpose": "default_single_idp"
                }
            )
            logger.info(f"Created default application for tenant {tenant_id}")
        
        return default_app