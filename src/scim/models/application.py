from typing import TYPE_CHECKING
from tortoise import fields
from tortoise.models import Model

if TYPE_CHECKING:
    from .tenant import Tenant
    from .user import User
    from .group import Group
    from .metadata import APIToken


class Application(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255)
    display_name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    external_id = fields.CharField(max_length=255, null=True)
    active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)
    settings = fields.JSONField(default=dict)
    metadata = fields.JSONField(default=dict)
    
    # Tenant relationship
    tenant: fields.ForeignKeyRelation["Tenant"] = fields.ForeignKeyField(
        "models.Tenant", related_name="applications", on_delete=fields.CASCADE
    )
    
    # Reverse relationships will be added by related models
    # api_tokens: fields.ReverseRelation["APIToken"]
    # users: fields.ReverseRelation["User"]
    # groups: fields.ReverseRelation["Group"]
    
    class Meta:
        table = "applications"
        unique_together = [("name", "tenant")]
        indexes = [
            ("name",),
            ("active",),
            ("external_id",),
        ]
    
    def __str__(self):
        return f"Application({self.name})"
    
    async def get_tenant_id(self) -> str:
        """Get the tenant ID for this application."""
        if not self.tenant_id:
            await self.fetch_related("tenant")
        return str(self.tenant_id)