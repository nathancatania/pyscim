from typing import TYPE_CHECKING
from tortoise import fields
from tortoise.models import Model

if TYPE_CHECKING:
    from .group import GroupMember
    from .application import Application


class User(Model):
    id = fields.UUIDField(pk=True)
    external_id = fields.CharField(max_length=255, null=True)
    user_name = fields.CharField(max_length=255)
    
    # Application relationship
    app: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="users", on_delete=fields.CASCADE
    )

    # Name attributes
    name_formatted = fields.TextField(null=True)
    name_family_name = fields.CharField(max_length=255, null=True)
    name_given_name = fields.CharField(max_length=255, null=True)
    name_middle_name = fields.CharField(max_length=255, null=True)
    name_honorific_prefix = fields.CharField(max_length=50, null=True)
    name_honorific_suffix = fields.CharField(max_length=50, null=True)

    # Core attributes
    display_name = fields.CharField(max_length=255, null=True)
    nick_name = fields.CharField(max_length=255, null=True)
    profile_url = fields.TextField(null=True)
    title = fields.CharField(max_length=255, null=True)
    user_type = fields.CharField(max_length=255, null=True)
    preferred_language = fields.CharField(max_length=50, null=True)
    locale = fields.CharField(max_length=50, null=True)
    timezone = fields.CharField(max_length=100, null=True)
    active = fields.BooleanField(default=True)
    password_hash = fields.TextField(null=True)

    # Enterprise User Extension
    employee_number = fields.CharField(max_length=255, null=True)
    cost_center = fields.CharField(max_length=255, null=True)
    organization = fields.CharField(max_length=255, null=True)
    division = fields.CharField(max_length=255, null=True)
    department = fields.CharField(max_length=255, null=True)
    manager: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="direct_reports", null=True, on_delete=fields.SET_NULL)

    # Metadata
    created = fields.DatetimeField(auto_now_add=True)
    modified = fields.DatetimeField(auto_now=True)
    etag = fields.CharField(max_length=255, null=True)
    resource_type = fields.CharField(max_length=50, default="User")
    metadata = fields.JSONField(default=dict)

    # Relations
    emails: fields.ReverseRelation["UserEmail"]
    phone_numbers: fields.ReverseRelation["UserPhoneNumber"]
    ims: fields.ReverseRelation["UserIM"]
    photos: fields.ReverseRelation["UserPhoto"]
    addresses: fields.ReverseRelation["UserAddress"]
    entitlements: fields.ReverseRelation["UserEntitlement"]
    roles: fields.ReverseRelation["UserRole"]
    x509_certificates: fields.ReverseRelation["UserX509Certificate"]
    group_memberships: fields.ReverseRelation["GroupMember"]

    class Meta:
        table = "users"
        unique_together = [("user_name", "app"), ("external_id", "app")]

    def __str__(self):
        return self.user_name


class UserEmail(Model):
    id = fields.UUIDField(pk=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField("models.User", related_name="emails", on_delete=fields.CASCADE)
    app: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="user_emails", on_delete=fields.CASCADE
    )
    value = fields.CharField(max_length=255)
    type = fields.CharField(max_length=50, null=True)
    primary_email = fields.BooleanField(default=False)
    display = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "user_emails"
        unique_together = [("user", "value")]


class UserPhoneNumber(Model):
    id = fields.UUIDField(pk=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField("models.User", related_name="phone_numbers", on_delete=fields.CASCADE)
    app: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="user_phone_numbers", on_delete=fields.CASCADE
    )
    value = fields.CharField(max_length=255)
    type = fields.CharField(max_length=50, null=True)
    primary_phone = fields.BooleanField(default=False)
    display = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "user_phone_numbers"
        unique_together = [("user", "value")]


class UserIM(Model):
    id = fields.UUIDField(pk=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField("models.User", related_name="ims", on_delete=fields.CASCADE)
    app: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="user_ims", on_delete=fields.CASCADE
    )
    value = fields.CharField(max_length=255)
    type = fields.CharField(max_length=50, null=True)
    primary_im = fields.BooleanField(default=False)
    display = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "user_ims"
        unique_together = [("user", "value")]


class UserPhoto(Model):
    id = fields.UUIDField(pk=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField("models.User", related_name="photos", on_delete=fields.CASCADE)
    app: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="user_photos", on_delete=fields.CASCADE
    )
    value = fields.TextField()
    type = fields.CharField(max_length=50, null=True)
    primary_photo = fields.BooleanField(default=False)
    display = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "user_photos"
        unique_together = [("user", "value")]


class UserAddress(Model):
    id = fields.UUIDField(pk=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField("models.User", related_name="addresses", on_delete=fields.CASCADE)
    app: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="user_addresses", on_delete=fields.CASCADE
    )
    formatted = fields.TextField(null=True)
    street_address = fields.TextField(null=True)
    locality = fields.CharField(max_length=255, null=True)
    region = fields.CharField(max_length=255, null=True)
    postal_code = fields.CharField(max_length=50, null=True)
    country = fields.CharField(max_length=100, null=True)
    type = fields.CharField(max_length=50, null=True)
    primary_address = fields.BooleanField(default=False)

    class Meta:
        table = "user_addresses"


class UserEntitlement(Model):
    id = fields.UUIDField(pk=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField("models.User", related_name="entitlements", on_delete=fields.CASCADE)
    app: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="user_entitlements", on_delete=fields.CASCADE
    )
    value = fields.CharField(max_length=255)
    display = fields.CharField(max_length=255, null=True)
    type = fields.CharField(max_length=50, null=True)
    primary_entitlement = fields.BooleanField(default=False)

    class Meta:
        table = "user_entitlements"
        unique_together = [("user", "value")]


class UserRole(Model):
    id = fields.UUIDField(pk=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField("models.User", related_name="roles", on_delete=fields.CASCADE)
    app: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="user_roles", on_delete=fields.CASCADE
    )
    value = fields.CharField(max_length=255)
    display = fields.CharField(max_length=255, null=True)
    type = fields.CharField(max_length=50, null=True)
    primary_role = fields.BooleanField(default=False)

    class Meta:
        table = "user_roles"
        unique_together = [("user", "value")]


class UserX509Certificate(Model):
    id = fields.UUIDField(pk=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField("models.User", related_name="x509_certificates", on_delete=fields.CASCADE)
    app: fields.ForeignKeyRelation["Application"] = fields.ForeignKeyField(
        "models.Application", related_name="user_x509_certificates", on_delete=fields.CASCADE
    )
    value = fields.TextField()
    display = fields.CharField(max_length=255, null=True)
    type = fields.CharField(max_length=50, null=True)
    primary_certificate = fields.BooleanField(default=False)

    class Meta:
        table = "user_x509_certificates"
        unique_together = [("user", "value")]
