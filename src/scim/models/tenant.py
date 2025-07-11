from tortoise import fields
from tortoise.models import Model


class Tenant(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    display_name = fields.CharField(max_length=255)
    external_id = fields.CharField(max_length=255, null=True, unique=True)
    active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)
    settings = fields.JSONField(default=dict)
    metadata = fields.JSONField(default=dict)

    # Relationships
    users: fields.ReverseRelation["User"]
    groups: fields.ReverseRelation["Group"]
    api_tokens: fields.ReverseRelation["APIToken"]

    class Meta:
        table = "tenants"
        ordering = ["name"]

    def __str__(self):
        return f"{self.display_name} ({self.name})"