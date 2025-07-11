from typing import TYPE_CHECKING
from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.postgres.fields import ArrayField

if TYPE_CHECKING:
    from .application import Application


class SchemaMetadata(Model):
    id = fields.CharField(max_length=255, pk=True)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    attributes = fields.JSONField()
    meta = fields.JSONField(default=dict)

    class Meta:
        table = "schema_metadata"


class ServiceProviderConfig(Model):
    id = fields.IntField(pk=True)
    documentation_uri = fields.TextField(null=True)
    patch_supported = fields.BooleanField(default=True)
    bulk_supported = fields.BooleanField(default=True)
    bulk_max_operations = fields.IntField(default=1000)
    bulk_max_payload_size = fields.IntField(default=1048576)
    filter_supported = fields.BooleanField(default=True)
    filter_max_results = fields.IntField(default=1000)
    change_password_supported = fields.BooleanField(default=True)
    sort_supported = fields.BooleanField(default=True)
    etag_supported = fields.BooleanField(default=True)
    authentication_schemes = fields.JSONField(default=list)
    meta = fields.JSONField(default=dict)

    class Meta:
        table = "service_provider_config"


class AuditLog(Model):
    id = fields.UUIDField(pk=True)
    timestamp = fields.DatetimeField(auto_now_add=True)
    operation = fields.CharField(max_length=50)
    resource_type = fields.CharField(max_length=50, null=True)
    resource_id = fields.UUIDField(null=True)
    resource_external_id = fields.CharField(max_length=255, null=True)
    actor_id = fields.CharField(max_length=255, null=True)
    ip_address = fields.CharField(max_length=45, null=True)
    user_agent = fields.TextField(null=True)
    request_id = fields.CharField(max_length=255, null=True)
    status_code = fields.IntField(null=True)
    error_message = fields.TextField(null=True)
    request_body = fields.JSONField(null=True)
    response_body = fields.JSONField(null=True)
    duration_ms = fields.IntField(null=True)
    
    # Application relationship
    app: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="audit_logs", on_delete=fields.CASCADE
    )

    class Meta:
        table = "audit_log"
        ordering = ["-timestamp"]


class APIToken(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255)
    token_hash = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    scopes = ArrayField(element_type="text", default=lambda: ["scim:read", "scim:write"])
    active = fields.BooleanField(default=True)
    expires_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    last_used_at = fields.DatetimeField(null=True)
    created_by = fields.CharField(max_length=255, null=True)
    metadata = fields.JSONField(default=dict)
    
    # Application relationship
    app: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="api_tokens", on_delete=fields.CASCADE
    )

    class Meta:
        table = "api_tokens"
        indexes = [("token_hash",)]
