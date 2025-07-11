from typing import TYPE_CHECKING
from tortoise import fields
from tortoise.models import Model

if TYPE_CHECKING:
    from .user import User
    from .application import Application


class Group(Model):
    id = fields.UUIDField(pk=True)
    external_id = fields.CharField(max_length=255, null=True)
    display_name = fields.CharField(max_length=255)
    
    # Application relationship
    app: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="groups", on_delete=fields.CASCADE
    )

    # Metadata
    created = fields.DatetimeField(auto_now_add=True)
    modified = fields.DatetimeField(auto_now=True)
    etag = fields.CharField(max_length=255, null=True)
    resource_type = fields.CharField(max_length=50, default="Group")
    metadata = fields.JSONField(default=dict)

    # Relations
    members: fields.ReverseRelation["GroupMember"]

    class Meta:
        table = "groups"
        unique_together = [("display_name", "app"), ("external_id", "app")]

    def __str__(self):
        return self.display_name


class GroupMember(Model):
    id = fields.UUIDField(pk=True)
    group: fields.ForeignKeyRelation[Group] = fields.ForeignKeyField("models.Group", related_name="members", on_delete=fields.CASCADE)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="group_memberships", null=True, on_delete=fields.CASCADE)
    nested_group: fields.ForeignKeyRelation[Group] = fields.ForeignKeyField("models.Group", related_name="parent_group_memberships", null=True, on_delete=fields.CASCADE)
    app: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="group_members", on_delete=fields.CASCADE
    )
    display = fields.CharField(max_length=255, null=True)
    type = fields.CharField(max_length=50, default="User")
    added_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "group_members"
        unique_together = [("group", "user"), ("group", "nested_group")]

    def clean(self):
        # Ensure either user or nested_group is set, but not both
        if (self.user and self.nested_group) or (not self.user and not self.nested_group):
            raise ValueError("Either user or nested_group must be set, but not both")
