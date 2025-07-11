import hashlib
import uuid
from typing import List, Optional, Any
from tortoise.exceptions import IntegrityError
from tortoise.transactions import atomic
from scim.models import (
    User, UserEmail, UserPhoneNumber, UserIM, UserPhoto, UserAddress,
    UserEntitlement, UserRole, UserX509Certificate, GroupMember
)
from scim.schemas import (
    UserRequest, UserResponse, Email, Name, Meta, ResourceType, 
    EnterpriseUserExtension, SCIMSchemaUri, Manager, MultiValuedAttribute, Address, UserGroup
)
from scim.exceptions import ResourceNotFound, ResourceAlreadyExists
from scim.utils import generate_etag, SCIMFilterParser, logger, parse_scim_path, find_matching_items
from scim.config import settings


class UserService:
    @staticmethod
    async def _resolve_manager_id(app_id: str, manager_value: str) -> Optional[str]:
        """Resolve manager reference to an ID using multiple lookup strategies.
        
        Attempts resolution in the following order:
        1. UUID - Direct UUID lookup
        2. Username - Exact username match
        3. Email - Check primary emails
        4. External ID - Identity provider's external ID
        
        This method handles various identifier formats from identity providers
        like Okta, which may send any of these identifier types.
        
        Args:
            app_id: The application ID
            manager_value: The manager reference (UUID, username, email, or external ID)
            
        Returns:
            The resolved manager UUID as a string, or None if not found
        """
        if not manager_value:
            return None
        
        # 1. Try to parse as UUID first
        try:
            manager_uuid = uuid.UUID(manager_value)
            # Verify the manager exists
            if await User.filter(app_id=app_id, id=manager_uuid).exists():
                logger.debug(f"Resolved manager by UUID: {manager_value}")
                return str(manager_uuid)
            else:
                logger.warning(f"Manager with ID {manager_value} does not exist in app {app_id}")
                return None
        except ValueError:
            # Not a UUID, continue with other lookup methods
            pass
        
        # 2. Try username lookup
        logger.debug(f"Manager value '{manager_value}' is not a UUID, attempting username lookup")
        manager_user = await User.filter(app_id=app_id, user_name=manager_value).first()
        if manager_user:
            logger.debug(f"Found manager by username: {manager_value} -> {manager_user.id}")
            return str(manager_user.id)
        
        # 3. Try email lookup
        logger.debug(f"Attempting email lookup for: {manager_value}")
        # Look for users who have this as a primary email
        email_match = await UserEmail.filter(
            app_id=app_id, 
            value=manager_value.lower()  # Emails are stored lowercase
        ).first()
        if email_match:
            manager_user = await email_match.user
            logger.debug(f"Found manager by email: {manager_value} -> {manager_user.id}")
            return str(manager_user.id)
        
        # 4. Try external_id lookup
        logger.debug(f"Attempting external_id lookup for: {manager_value}")
        manager_user = await User.filter(app_id=app_id, external_id=manager_value).first()
        if manager_user:
            logger.debug(f"Found manager by external_id: {manager_value} -> {manager_user.id}")
            return str(manager_user.id)
        
        # No match found with any method
        logger.warning(f"Manager reference '{manager_value}' not found using any lookup method in app {app_id}")
        return None
    
    @staticmethod
    def _store_manager_reference(user: User, manager_value: str, manager_display_name: Optional[str] = None) -> None:
        """Store the original manager reference in user metadata.
        
        We always store the original manager reference sent by the identity provider,
        regardless of whether it can be resolved to a SCIM user. This ensures we can:
        1. Always return the exact value the IdP sent
        2. Maintain the ref field separately based on resolution status
        3. Preserve display names provided by the IdP
        
        Args:
            user: The user object to update
            manager_value: The original manager reference (email, username, external_id, or UUID)
            manager_display_name: Optional display name for the manager
        """
        if not user.metadata:
            user.metadata = {}
        
        # Always store the original manager reference
        user.metadata['manager_reference'] = {
            'value': manager_value,
            'display_name': manager_display_name
        }
        logger.debug(f"Stored manager reference '{manager_value}' for user {user.user_name}")
    
    
    @staticmethod
    async def _resolve_pending_managers(app_id: str, new_user: User) -> int:
        """Check if a newly created/updated user resolves any pending manager references.
        
        When a user is created or updated, this method checks if any other users
        have unresolved manager references that might now be resolvable with the
        new/updated user's identifiers.
        
        Args:
            app_id: The application ID
            new_user: The newly created or updated user
            
        Returns:
            Number of manager references that were resolved
        """
        resolved_count = 0
        
        # Build list of identifiers that could match unresolved references
        possible_identifiers = [
            str(new_user.id),  # UUID
            new_user.user_name,  # Username
            new_user.external_id  # External ID
        ]
        
        # Add all user emails
        user_emails = await UserEmail.filter(app_id=app_id, user=new_user).all()
        for email in user_emails:
            possible_identifiers.append(email.value)
        
        # Remove None values
        possible_identifiers = [id for id in possible_identifiers if id]
        
        if not possible_identifiers:
            return 0
        
        logger.debug(f"Checking if user {new_user.user_name} resolves pending managers. Identifiers: {possible_identifiers}")
        
        # Find all users with unresolved manager references
        # Note: Tortoise ORM doesn't support direct JSON queries, so we need to fetch and filter
        users_with_unresolved = await User.filter(
            app_id=app_id,
            metadata__isnull=False
        ).exclude(id=new_user.id)  # Don't check the new user itself
        
        for user in users_with_unresolved:
            if not user.metadata or 'manager_reference' not in user.metadata:
                continue
            
            # Skip if already has a resolved manager
            if user.manager_id:
                continue
            
            manager_ref = user.metadata['manager_reference']
            manager_value = manager_ref.get('value')
            
            # Check if the reference matches any of the new user's identifiers
            if manager_value and manager_value in possible_identifiers:
                logger.info(f"Resolving manager reference for user {user.user_name}: {manager_value} -> {new_user.id}")
                
                # Update the user's manager_id (keep the original reference in metadata)
                user.manager_id = str(new_user.id)
                
                # Generate new ETag and save
                user.etag = generate_etag(user)
                await user.save()
                
                resolved_count += 1
        
        if resolved_count > 0:
            logger.info(f"Resolved {resolved_count} pending manager reference(s) with user {new_user.user_name}")
        
        return resolved_count
    
    @staticmethod
    async def create_user(app_id: str, user_data: UserRequest) -> UserResponse:
        try:
            # Hash password if provided
            password_hash = None
            if user_data.password:
                password_hash = hashlib.sha256(user_data.password.encode()).hexdigest()
            
            # Extract enterprise extension data
            enterprise_data = None
            manager_id = None
            manager_value = None
            manager_display_name = None
            
            if user_data.urn_ietf_params_scim_schemas_extension_enterprise_2_0_User:
                enterprise_data = user_data.urn_ietf_params_scim_schemas_extension_enterprise_2_0_User
                # Extract manager information if provided
                if enterprise_data.manager and enterprise_data.manager.value:
                    manager_value = enterprise_data.manager.value
                    manager_display_name = enterprise_data.manager.display_name
                    manager_id = await UserService._resolve_manager_id(app_id, manager_value)
            
            # Create user
            user = await User.create(
                app_id=app_id,
                user_name=user_data.user_name,
                external_id=user_data.external_id,
                name_formatted=user_data.name.formatted if user_data.name else None,
                name_family_name=user_data.name.family_name if user_data.name else None,
                name_given_name=user_data.name.given_name if user_data.name else None,
                name_middle_name=user_data.name.middle_name if user_data.name else None,
                name_honorific_prefix=user_data.name.honorific_prefix if user_data.name else None,
                name_honorific_suffix=user_data.name.honorific_suffix if user_data.name else None,
                display_name=user_data.display_name,
                nick_name=user_data.nick_name,
                profile_url=user_data.profile_url,
                title=user_data.title,
                user_type=user_data.user_type,
                preferred_language=user_data.preferred_language,
                locale=user_data.locale,
                timezone=user_data.timezone,
                active=user_data.active,
                password_hash=password_hash,
                employee_number=enterprise_data.employee_number if enterprise_data else None,
                cost_center=enterprise_data.cost_center if enterprise_data else None,
                organization=enterprise_data.organization if enterprise_data else None,
                division=enterprise_data.division if enterprise_data else None,
                department=enterprise_data.department if enterprise_data else None,
                manager_id=manager_id,
            )
            
            # Create multi-valued attributes
            if user_data.emails:
                for email in user_data.emails:
                    await UserEmail.create(
                        app_id=app_id,
                        user=user,
                        value=email.value,
                        type=email.type,
                        primary_email=email.primary,
                        display=email.display
                    )
            
            if user_data.phone_numbers:
                for phone in user_data.phone_numbers:
                    await UserPhoneNumber.create(
                        app_id=app_id,
                        user=user,
                        value=phone.value,
                        type=phone.type,
                        primary_phone=phone.primary,
                        display=phone.display
                    )
            
            if user_data.ims:
                for im in user_data.ims:
                    await UserIM.create(
                        app_id=app_id,
                        user=user,
                        value=im.value,
                        type=im.type,
                        primary_im=im.primary,
                        display=im.display
                    )
            
            if user_data.photos:
                for photo in user_data.photos:
                    await UserPhoto.create(
                        app_id=app_id,
                        user=user,
                        value=photo.value,
                        type=photo.type,
                        primary_photo=photo.primary,
                        display=photo.display
                    )
            
            if user_data.addresses:
                for address in user_data.addresses:
                    await UserAddress.create(
                        app_id=app_id,
                        user=user,
                        formatted=address.formatted,
                        street_address=address.street_address,
                        locality=address.locality,
                        region=address.region,
                        postal_code=address.postal_code,
                        country=address.country,
                        type=address.type,
                        primary_address=address.primary
                    )
            
            if user_data.entitlements:
                for entitlement in user_data.entitlements:
                    await UserEntitlement.create(
                        app_id=app_id,
                        user=user,
                        value=entitlement.value,
                        type=entitlement.type,
                        primary_entitlement=entitlement.primary,
                        display=entitlement.display
                    )
            
            if user_data.roles:
                for role in user_data.roles:
                    await UserRole.create(
                        app_id=app_id,
                        user=user,
                        value=role.value,
                        type=role.type,
                        primary_role=role.primary,
                        display=role.display
                    )
            
            if user_data.x509_certificates:
                for cert in user_data.x509_certificates:
                    await UserX509Certificate.create(
                        app_id=app_id,
                        user=user,
                        value=cert.value,
                        type=cert.type,
                        primary_certificate=cert.primary,
                        display=cert.display
                    )
            
            # Store the original manager reference if provided
            if manager_value:
                UserService._store_manager_reference(user, manager_value, manager_display_name)
            
            # Generate ETag
            user.etag = generate_etag(user)
            await user.save()
            
            # Check if this new user resolves any pending manager references
            await UserService._resolve_pending_managers(app_id, user)
            
            return await UserService._to_response(user)
            
        except IntegrityError as e:
            if "user_name" in str(e):
                raise ResourceAlreadyExists("User", "userName", user_data.user_name)
            elif "external_id" in str(e):
                raise ResourceAlreadyExists("User", "externalId", user_data.external_id)
            raise
    
    @staticmethod
    async def get_user(app_id: str, user_id: str) -> UserResponse:
        user = await User.filter(app_id=app_id, id=user_id).prefetch_related(
            "emails", "phone_numbers", "ims", "photos", 
            "addresses", "entitlements", "roles", "x509_certificates",
            "manager"
        ).first()
        
        if not user:
            raise ResourceNotFound("User", user_id)
        
        return await UserService._to_response(user)
    
    @staticmethod
    async def get_user_by_username(app_id: str, username: str) -> UserResponse:
        user = await User.filter(app_id=app_id, user_name=username).prefetch_related(
            "emails", "phone_numbers", "ims", "photos", 
            "addresses", "entitlements", "roles", "x509_certificates",
            "manager"
        ).first()
        
        if not user:
            raise ResourceNotFound("User", username)
        
        return await UserService._to_response(user)
    
    @staticmethod
    async def update_user(app_id: str, user_id: str, user_data: UserRequest) -> UserResponse:
        user = await User.filter(app_id=app_id, id=user_id).first()
        if not user:
            raise ResourceNotFound("User", user_id)
        
        # Update basic fields
        user.user_name = user_data.user_name
        user.external_id = user_data.external_id
        user.display_name = user_data.display_name
        user.nick_name = user_data.nick_name
        user.profile_url = user_data.profile_url
        user.title = user_data.title
        user.user_type = user_data.user_type
        user.preferred_language = user_data.preferred_language
        user.locale = user_data.locale
        user.timezone = user_data.timezone
        user.active = user_data.active
        
        # Update name fields
        if user_data.name:
            user.name_formatted = user_data.name.formatted
            user.name_family_name = user_data.name.family_name
            user.name_given_name = user_data.name.given_name
            user.name_middle_name = user_data.name.middle_name
            user.name_honorific_prefix = user_data.name.honorific_prefix
            user.name_honorific_suffix = user_data.name.honorific_suffix
        else:
            user.name_formatted = None
            user.name_family_name = None
            user.name_given_name = None
            user.name_middle_name = None
            user.name_honorific_prefix = None
            user.name_honorific_suffix = None
        
        # Update enterprise extension fields
        manager_value = None
        manager_display_name = None
        
        if user_data.urn_ietf_params_scim_schemas_extension_enterprise_2_0_User:
            enterprise_data = user_data.urn_ietf_params_scim_schemas_extension_enterprise_2_0_User
            user.employee_number = enterprise_data.employee_number
            user.cost_center = enterprise_data.cost_center
            user.organization = enterprise_data.organization
            user.division = enterprise_data.division
            user.department = enterprise_data.department
            
            # Update manager
            if enterprise_data.manager and enterprise_data.manager.value:
                manager_value = enterprise_data.manager.value
                manager_display_name = enterprise_data.manager.display_name
                user.manager_id = await UserService._resolve_manager_id(app_id, manager_value)
                
                # Always store the original manager reference
                UserService._store_manager_reference(user, manager_value, manager_display_name)
            else:
                # Manager explicitly removed
                user.manager_id = None
                # Clear manager reference from metadata
                if user.metadata and 'manager_reference' in user.metadata:
                    del user.metadata['manager_reference']
        else:
            # Enterprise extension removed entirely
            user.employee_number = None
            user.cost_center = None
            user.organization = None
            user.division = None
            user.department = None
            user.manager_id = None
            # Clear manager reference from metadata
            if user.metadata and 'manager_reference' in user.metadata:
                del user.metadata['manager_reference']
        
        # Update password if provided
        if user_data.password:
            user.password_hash = hashlib.sha256(user_data.password.encode()).hexdigest()
        
        # Update multi-valued attributes (delete and recreate for simplicity)
        await UserEmail.filter(app_id=app_id, user=user).delete()
        if user_data.emails:
            for email in user_data.emails:
                await UserEmail.create(
                    app_id=app_id,
                    user=user,
                    value=email.value,
                    type=email.type,
                    primary_email=email.primary,
                    display=email.display
                )
        
        await UserPhoneNumber.filter(app_id=app_id, user=user).delete()
        if user_data.phone_numbers:
            for phone in user_data.phone_numbers:
                await UserPhoneNumber.create(
                    app_id=app_id,
                    user=user,
                    value=phone.value,
                    type=phone.type,
                    primary_phone=phone.primary,
                    display=phone.display
                )
        
        await UserIM.filter(app_id=app_id, user=user).delete()
        if user_data.ims:
            for im in user_data.ims:
                await UserIM.create(
                    app_id=app_id,
                    user=user,
                    value=im.value,
                    type=im.type,
                    primary_im=im.primary,
                    display=im.display
                )
        
        await UserPhoto.filter(app_id=app_id, user=user).delete()
        if user_data.photos:
            for photo in user_data.photos:
                await UserPhoto.create(
                    app_id=app_id,
                    user=user,
                    value=photo.value,
                    type=photo.type,
                    primary_photo=photo.primary,
                    display=photo.display
                )
        
        await UserAddress.filter(app_id=app_id, user=user).delete()
        if user_data.addresses:
            for address in user_data.addresses:
                await UserAddress.create(
                    app_id=app_id,
                    user=user,
                    formatted=address.formatted,
                    street_address=address.street_address,
                    locality=address.locality,
                    region=address.region,
                    postal_code=address.postal_code,
                    country=address.country,
                    type=address.type,
                    primary_address=address.primary
                )
        
        await UserEntitlement.filter(app_id=app_id, user=user).delete()
        if user_data.entitlements:
            for entitlement in user_data.entitlements:
                await UserEntitlement.create(
                    app_id=app_id,
                    user=user,
                    value=entitlement.value,
                    type=entitlement.type,
                    primary_entitlement=entitlement.primary,
                    display=entitlement.display
                )
        
        await UserRole.filter(app_id=app_id, user=user).delete()
        if user_data.roles:
            for role in user_data.roles:
                await UserRole.create(
                    app_id=app_id,
                    user=user,
                    value=role.value,
                    type=role.type,
                    primary_role=role.primary,
                    display=role.display
                )
        
        await UserX509Certificate.filter(app_id=app_id, user=user).delete()
        if user_data.x509_certificates:
            for cert in user_data.x509_certificates:
                await UserX509Certificate.create(
                    app_id=app_id,
                    user=user,
                    value=cert.value,
                    type=cert.type,
                    primary_certificate=cert.primary,
                    display=cert.display
                )
        
        # Generate new ETag
        user.etag = generate_etag(user)
        await user.save()
        
        # Check if this updated user resolves any pending manager references
        # (in case username, email, or external_id changed)
        await UserService._resolve_pending_managers(app_id, user)
        
        return await UserService._to_response(user)
    
    @staticmethod
    async def delete_user(app_id: str, user_id: str) -> None:
        user = await User.filter(app_id=app_id, id=user_id).first()
        if not user:
            raise ResourceNotFound("User", user_id)
        
        await user.delete()
    
    @staticmethod
    @atomic()
    async def patch_user(app_id: str, user_id: str, operations: List) -> UserResponse:
        """Apply PATCH operations to a user as per RFC 7644 Section 3.5.2"""
        from scim.utils import logger
        
        logger.debug(f"patch_user: Starting patch for user {user_id} in app {app_id}")
        user = await User.filter(app_id=app_id, id=user_id).prefetch_related(
            "emails", "phone_numbers", "ims", "photos", 
            "addresses", "entitlements", "roles", "x509_certificates",
            "manager"
        ).first()
        
        if not user:
            raise ResourceNotFound("User", user_id)
        
        logger.debug(f"patch_user: User loaded, current manager_id: {user.manager_id}")
        
        for idx, operation in enumerate(operations):
            op = operation.op.lower()
            path = operation.path
            value = operation.value
            
            logger.debug(f"patch_user: Processing operation {idx + 1} - op: {op}, path: {path}, value: {value}")
            
            # Enforce path requirements per RFC 7644
            if op == "remove" and not path:
                raise ValueError(f"Operation {idx + 1}: 'path' is required for 'remove' operations")
            
            # Handle operations without path
            if not path:
                if op == "replace" and isinstance(value, dict):
                    await UserService._apply_replace_all(app_id, user, value)
                elif op == "add" and isinstance(value, dict):
                    # Add operation without path adds/replaces attributes
                    await UserService._apply_replace_all(app_id, user, value)
                else:
                    raise ValueError(f"Operation {idx + 1}: Invalid operation '{op}' without path")
                continue
            
            # Parse the SCIM path
            try:
                parsed_path = parse_scim_path(path)
                logger.debug(f"patch_user: Parsed path - {parsed_path}")
                
                # Handle schema updates for fully qualified paths
                if parsed_path.schema_uri:
                    await UserService._update_schemas(user, parsed_path.schema_uri)
                
                # Apply the operation based on the parsed path
                await UserService._apply_patch_with_parsed_path(
                    app_id, user, op, parsed_path, value, idx
                )
                
            except ValueError as e:
                raise ValueError(f"Operation {idx + 1}: Invalid path '{path}' - {str(e)}")
            except Exception as e:
                raise ValueError(f"Operation {idx + 1} failed: {str(e)}")
        
        logger.debug(f"patch_user: After operations, manager_id: {user.manager_id}")
        
        # Generate new ETag and save
        old_etag = user.etag
        user.etag = generate_etag(user)
        logger.debug(f"patch_user: ETag changed from {old_etag} to {user.etag}")
        
        try:
            await user.save()
            logger.debug("patch_user: User saved successfully")
        except Exception as e:
            logger.error(f"patch_user: Error saving user: {str(e)}")
            raise
        
        # Reload to verify save
        saved_user = await User.filter(app_id=app_id, id=user_id).first()
        logger.debug(f"patch_user: After reload, manager_id: {saved_user.manager_id}")
        
        # Check if this patched user resolves any pending manager references
        # (in case username, email, or external_id changed)
        await UserService._resolve_pending_managers(app_id, user)
        
        return await UserService._to_response(user)
    
    @staticmethod
    async def _apply_replace_all(app_id: str, user: User, values: dict):
        """Apply replace operation to multiple attributes"""
        # Map of SCIM attribute names to model field names
        field_map = {
            'userName': 'user_name',
            'externalId': 'external_id',
            'displayName': 'display_name',
            'nickName': 'nick_name',
            'profileUrl': 'profile_url',
            'title': 'title',
            'userType': 'user_type',
            'preferredLanguage': 'preferred_language',
            'locale': 'locale',
            'timezone': 'timezone',
            'active': 'active',
        }
        
        for attr, value in values.items():
            if attr in field_map:
                setattr(user, field_map[attr], value)
    
    @staticmethod
    async def _apply_patch_simple(app_id: str, user: User, op: str, attribute: str, value):
        """Apply patch operation to a simple attribute"""
        from scim.utils import logger
        
        logger.debug(f"_apply_patch_simple: Called with op={op}, attribute={attribute}, value={value}")
        
        # Check if this is an enterprise extension path
        if attribute.startswith("urn:ietf:params:scim:schemas:extension:enterprise:2.0:User:"):
            logger.debug("_apply_patch_simple: Detected enterprise extension path")
            # Extract the field name after the last colon
            enterprise_field = attribute.split(":")[-1]
            logger.debug(f"_apply_patch_simple: Extracted enterprise field: {enterprise_field}")
            
            enterprise_field_map = {
                'employeeNumber': 'employee_number',
                'costCenter': 'cost_center',
                'organization': 'organization',
                'division': 'division',
                'department': 'department',
            }
            
            if enterprise_field in enterprise_field_map:
                field_name = enterprise_field_map[enterprise_field]
                logger.debug(f"_apply_patch_simple: Mapped to field name: {field_name}")
                if op == "replace" or op == "add":
                    setattr(user, field_name, value)
                    logger.debug(f"_apply_patch_simple: Set {field_name} = {value}")
                elif op == "remove":
                    setattr(user, field_name, None)
                    logger.debug(f"_apply_patch_simple: Removed {field_name}")
            elif enterprise_field == "manager":
                logger.debug("_apply_patch_simple: Processing manager field")
                if op == "replace" or op == "add":
                    manager_id_to_set = None
                    manager_display_name = None
                    
                    # Extract manager value and display name
                    if isinstance(value, dict) and "value" in value:
                        manager_id_to_set = value["value"]
                        manager_display_name = value.get("displayName")
                        logger.debug(f"_apply_patch_simple: Manager ID from dict value: {manager_id_to_set}")
                    else:
                        manager_id_to_set = value
                        logger.debug(f"_apply_patch_simple: Manager ID directly: {manager_id_to_set}")
                    
                    # Resolve the manager ID
                    if manager_id_to_set:
                        resolved_manager_id = await UserService._resolve_manager_id(app_id, manager_id_to_set)
                        user.manager_id = resolved_manager_id
                        
                        # Always store the original manager reference
                        UserService._store_manager_reference(user, manager_id_to_set, manager_display_name)
                        
                        if resolved_manager_id:
                            logger.debug(f"_apply_patch_simple: Set manager_id = {resolved_manager_id}")
                        else:
                            logger.debug(f"_apply_patch_simple: Could not resolve manager '{manager_id_to_set}'")
                    else:
                        logger.warning("_apply_patch_simple: Manager ID is None or empty")
                        user.manager_id = None
                        # Clear manager reference from metadata
                        if user.metadata and 'manager_reference' in user.metadata:
                            del user.metadata['manager_reference']
                elif op == "remove":
                    user.manager_id = None
                    # Clear manager reference from metadata
                    if user.metadata and 'manager_reference' in user.metadata:
                        del user.metadata['manager_reference']
                    logger.debug("_apply_patch_simple: Removed manager_id and cleared metadata")
            else:
                logger.warning(f"_apply_patch_simple: Unknown enterprise field: {enterprise_field}")
            return
        
        # Map of SCIM attribute names to model field names
        field_map = {
            'userName': 'user_name',
            'externalId': 'external_id',
            'displayName': 'display_name',
            'nickName': 'nick_name',
            'profileUrl': 'profile_url',
            'title': 'title',
            'userType': 'user_type',
            'preferredLanguage': 'preferred_language',
            'locale': 'locale',
            'timezone': 'timezone',
            'active': 'active',
        }
        
        if attribute in field_map:
            field_name = field_map[attribute]
            if op == "replace" or op == "add":
                setattr(user, field_name, value)
            elif op == "remove":
                setattr(user, field_name, None)
        elif attribute == "emails":
            await UserService._patch_multi_valued(app_id, user, op, UserEmail, value, "emails")
        elif attribute == "phoneNumbers":
            await UserService._patch_multi_valued(app_id, user, op, UserPhoneNumber, value, "phone_numbers")
        elif attribute == "ims":
            await UserService._patch_multi_valued(app_id, user, op, UserIM, value, "ims")
        elif attribute == "photos":
            await UserService._patch_multi_valued(app_id, user, op, UserPhoto, value, "photos")
        elif attribute == "addresses":
            await UserService._patch_addresses(app_id, user, op, value)
        elif attribute == "entitlements":
            await UserService._patch_multi_valued(app_id, user, op, UserEntitlement, value, "entitlements")
        elif attribute == "roles":
            await UserService._patch_multi_valued(app_id, user, op, UserRole, value, "roles")
        elif attribute == "x509Certificates":
            await UserService._patch_multi_valued(app_id, user, op, UserX509Certificate, value, "x509_certificates")
    
    @staticmethod
    async def _apply_patch_complex(app_id: str, user: User, op: str, path_parts: List[str], value):
        """Apply patch operation to a complex/nested attribute"""
        attribute = path_parts[0]
        sub_attribute = path_parts[1] if len(path_parts) > 1 else None
        
        if attribute == "name":
            name_field_map = {
                'formatted': 'name_formatted',
                'familyName': 'name_family_name',
                'givenName': 'name_given_name',
                'middleName': 'name_middle_name',
                'honorificPrefix': 'name_honorific_prefix',
                'honorificSuffix': 'name_honorific_suffix',
            }
            
            if sub_attribute and sub_attribute in name_field_map:
                field_name = name_field_map[sub_attribute]
                if op == "replace" or op == "add":
                    setattr(user, field_name, value)
                elif op == "remove":
                    setattr(user, field_name, None)
            elif not sub_attribute and op == "replace" and isinstance(value, dict):
                # Replace entire name object
                for scim_field, db_field in name_field_map.items():
                    setattr(user, db_field, value.get(scim_field))
        
        elif attribute.startswith("urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"):
            # Handle enterprise extension attributes
            enterprise_parts = attribute.split(":")
            if len(enterprise_parts) > 8:
                enterprise_attr = enterprise_parts[8]
                enterprise_field_map = {
                    'employeeNumber': 'employee_number',
                    'costCenter': 'cost_center',
                    'organization': 'organization',
                    'division': 'division',
                    'department': 'department',
                }
                
                if enterprise_attr in enterprise_field_map:
                    field_name = enterprise_field_map[enterprise_attr]
                    if op == "replace" or op == "add":
                        setattr(user, field_name, value)
                    elif op == "remove":
                        setattr(user, field_name, None)
                elif enterprise_attr == "manager":
                    if op == "replace" or op == "add":
                        manager_value = None
                        manager_display_name = None
                        
                        # Extract manager information
                        if isinstance(value, dict) and "value" in value:
                            manager_value = value["value"]
                            manager_display_name = value.get("displayName")
                        else:
                            manager_value = value
                        
                        if manager_value:
                            resolved_id = await UserService._resolve_manager_id(app_id, manager_value)
                            user.manager_id = resolved_id
                            
                            # Always store the original manager reference
                            UserService._store_manager_reference(user, manager_value, manager_display_name)
                        else:
                            user.manager_id = None
                            # Clear manager reference from metadata
                            if user.metadata and 'manager_reference' in user.metadata:
                                del user.metadata['manager_reference']
                    elif op == "remove":
                        user.manager_id = None
                        # Clear manager reference from metadata
                        if user.metadata and 'manager_reference' in user.metadata:
                            del user.metadata['manager_reference']
    
    @staticmethod
    async def _patch_multi_valued(app_id: str, user: User, op: str, model_class, value, relation_name: str):
        """Handle patch operations for multi-valued attributes"""
        if op == "add":
            if isinstance(value, list):
                for item in value:
                    await UserService._create_multi_valued_item(app_id, user, model_class, item)
            else:
                await UserService._create_multi_valued_item(app_id, user, model_class, value)
        
        elif op == "remove":
            if value is None:
                # Remove all values
                await model_class.filter(app_id=app_id, user=user).delete()
            elif isinstance(value, list):
                # Remove specific values
                for item in value:
                    if isinstance(item, dict) and "value" in item:
                        await model_class.filter(app_id=app_id, user=user, value=item["value"]).delete()
        
        elif op == "replace":
            # Replace all values
            await model_class.filter(app_id=app_id, user=user).delete()
            if isinstance(value, list):
                for item in value:
                    await UserService._create_multi_valued_item(app_id, user, model_class, item)
            elif value is not None:
                await UserService._create_multi_valued_item(app_id, user, model_class, value)
    
    @staticmethod
    async def _create_multi_valued_item(app_id: str, user: User, model_class, item_data: dict):
        """Create a single multi-valued attribute item"""
        if not isinstance(item_data, dict):
            return
        
        # Map common fields
        create_data = {"app_id": app_id, "user": user}
        
        if "value" in item_data:
            create_data["value"] = item_data["value"]
        if "type" in item_data:
            create_data["type"] = item_data["type"]
        if "display" in item_data:
            create_data["display"] = item_data["display"]
        
        # Handle primary field based on model
        if model_class == UserEmail and "primary" in item_data:
            create_data["primary_email"] = item_data["primary"]
        elif model_class == UserPhoneNumber and "primary" in item_data:
            create_data["primary_phone"] = item_data["primary"]
        elif model_class == UserIM and "primary" in item_data:
            create_data["primary_im"] = item_data["primary"]
        elif model_class == UserPhoto and "primary" in item_data:
            create_data["primary_photo"] = item_data["primary"]
        elif model_class == UserEntitlement and "primary" in item_data:
            create_data["primary_entitlement"] = item_data["primary"]
        elif model_class == UserRole and "primary" in item_data:
            create_data["primary_role"] = item_data["primary"]
        elif model_class == UserX509Certificate and "primary" in item_data:
            create_data["primary_certificate"] = item_data["primary"]
        
        await model_class.create(**create_data)
    
    @staticmethod
    async def _patch_addresses(app_id: str, user: User, op: str, value):
        """Handle patch operations for addresses"""
        if op == "add":
            if isinstance(value, list):
                for addr in value:
                    await UserService._create_address(app_id, user, addr)
            else:
                await UserService._create_address(app_id, user, value)
        
        elif op == "remove":
            if value is None:
                # Remove all addresses
                await UserAddress.filter(app_id=app_id, user=user).delete()
            elif isinstance(value, list):
                # Remove specific addresses - addresses don't have a unique value field
                # so we can't easily identify which to remove
                pass
        
        elif op == "replace":
            # Replace all addresses
            await UserAddress.filter(app_id=app_id, user=user).delete()
            if isinstance(value, list):
                for addr in value:
                    await UserService._create_address(app_id, user, addr)
            elif value is not None:
                await UserService._create_address(app_id, user, value)
    
    @staticmethod
    async def _create_address(app_id: str, user: User, addr_data: dict):
        """Create a single address"""
        if not isinstance(addr_data, dict):
            return
        
        await UserAddress.create(
            app_id=app_id,
            user=user,
            formatted=addr_data.get("formatted"),
            street_address=addr_data.get("streetAddress"),
            locality=addr_data.get("locality"),
            region=addr_data.get("region"),
            postal_code=addr_data.get("postalCode"),
            country=addr_data.get("country"),
            type=addr_data.get("type"),
            primary_address=addr_data.get("primary", False)
        )
    
    @staticmethod
    async def list_users(
        app_id: str,
        offset: int = 0,
        limit: int = 100,
        filter_query: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "ascending"
    ) -> tuple[List[UserResponse], int]:
        query = User.filter(app_id=app_id)
        
        # Apply filter if provided
        if filter_query:
            try:
                parser = SCIMFilterParser(resource_type='User')
                filter_q = parser.parse(filter_query)
                query = query.filter(filter_q)
            except ValueError as e:
                # Per RFC 7644, invalid filters should return 400 Bad Request
                from scim.utils import logger
                logger.warning(f"Invalid SCIM filter: {filter_query} - {str(e)}")
                raise ValueError(f"Invalid filter: {str(e)}")
        
        # Get total count after filtering
        total_count = await query.count()
        
        # Apply sorting
        if sort_by:
            # Map SCIM attributes to model fields for sorting
            sort_field_map = {
                'userName': 'user_name',
                'externalId': 'external_id',
                'displayName': 'display_name',
                'meta.created': 'created',
                'meta.lastModified': 'modified',
            }
            sort_field = sort_field_map.get(sort_by, sort_by)
            order_prefix = "-" if sort_order == "descending" else ""
            query = query.order_by(f"{order_prefix}{sort_field}")
        else:
            query = query.order_by("created")
        
        # Apply pagination
        users = await query.offset(offset).limit(limit).prefetch_related(
            "emails", "phone_numbers", "ims", "photos", 
            "addresses", "entitlements", "roles", "x509_certificates",
            "manager"
        )
        
        responses = []
        for user in users:
            responses.append(await UserService._to_response(user))
        
        return responses, total_count
    
    @staticmethod
    async def _to_response(user: User) -> UserResponse:
        # Build name object
        name = None
        if any([user.name_formatted, user.name_family_name, user.name_given_name]):
            name = Name(
                formatted=user.name_formatted,
                family_name=user.name_family_name,
                given_name=user.name_given_name,
                middle_name=user.name_middle_name,
                honorific_prefix=user.name_honorific_prefix,
                honorific_suffix=user.name_honorific_suffix
            )
        
        # Build emails
        emails = []
        for email in await user.emails.all():
            emails.append(Email(
                value=email.value,
                type=email.type,
                primary=email.primary_email,
                display=email.display
            ))
        
        # Build phone numbers
        phone_numbers = []
        for phone in await user.phone_numbers.all():
            phone_numbers.append(MultiValuedAttribute(
                value=phone.value,
                type=phone.type,
                primary=phone.primary_phone,
                display=phone.display
            ))
        
        # Build IMs
        ims = []
        for im in await user.ims.all():
            ims.append(MultiValuedAttribute(
                value=im.value,
                type=im.type,
                primary=im.primary_im,
                display=im.display
            ))
        
        # Build photos
        photos = []
        for photo in await user.photos.all():
            photos.append(MultiValuedAttribute(
                value=photo.value,
                type=photo.type,
                primary=photo.primary_photo,
                display=photo.display
            ))
        
        # Build addresses
        addresses = []
        for address in await user.addresses.all():
            addresses.append(Address(
                formatted=address.formatted,
                street_address=address.street_address,
                locality=address.locality,
                region=address.region,
                postal_code=address.postal_code,
                country=address.country,
                type=address.type,
                primary=address.primary_address
            ))
        
        # Build entitlements
        entitlements = []
        for entitlement in await user.entitlements.all():
            entitlements.append(MultiValuedAttribute(
                value=entitlement.value,
                type=entitlement.type,
                primary=entitlement.primary_entitlement,
                display=entitlement.display
            ))
        
        # Build roles
        roles = []
        for role in await user.roles.all():
            roles.append(MultiValuedAttribute(
                value=role.value,
                type=role.type,
                primary=role.primary_role,
                display=role.display
            ))
        
        # Build x509 certificates
        x509_certificates = []
        for cert in await user.x509_certificates.all():
            x509_certificates.append(MultiValuedAttribute(
                value=cert.value,
                type=cert.type,
                primary=cert.primary_certificate,
                display=cert.display
            ))
        
        # Build groups
        groups = []
        # Get all group memberships where this user is a member
        group_memberships = await GroupMember.filter(
            app_id=user.app_id,
            user=user
        ).prefetch_related("group")
        
        for membership in group_memberships:
            if membership.group:
                groups.append(UserGroup(
                    value=str(membership.group.id),
                    ref=f"{settings.api_prefix}/Groups/{membership.group.id}",
                    display=membership.group.display_name,
                    type="direct"
                ))
        
        # Build enterprise extension
        enterprise_ext = None
        manager = None
        
        # Check if user has a manager reference in metadata
        if user.metadata and 'manager_reference' in user.metadata:
            manager_ref = user.metadata['manager_reference']
            manager_value = manager_ref.get('value')
            manager_display_name = manager_ref.get('display_name')
            
            # Build manager object with original value
            if manager_value:
                # Check if we have a resolved manager_id for the ref field
                ref = None
                if user.manager_id:
                    ref = f"{settings.api_prefix}/Users/{user.manager_id}"
                
                manager = Manager(
                    value=manager_value,
                    ref=ref,
                    display_name=manager_display_name
                )
        
        if any([user.employee_number, user.cost_center, user.organization, 
                user.division, user.department, manager]):
            enterprise_ext = EnterpriseUserExtension(
                employee_number=user.employee_number,
                cost_center=user.cost_center,
                organization=user.organization,
                division=user.division,
                department=user.department,
                manager=manager
            )
        
        # Build meta
        meta = Meta(
            resource_type=ResourceType.USER,
            created=user.created,
            last_modified=user.modified,
            location=f"{settings.api_prefix}/Users/{user.id}",
            version=user.etag
        )
        
        # Build schemas list
        schemas = [SCIMSchemaUri.USER.value]
        if enterprise_ext:
            schemas.append(SCIMSchemaUri.ENTERPRISE_USER.value)
        
        return UserResponse(
            schemas=schemas,
            id=str(user.id),
            user_name=user.user_name,
            external_id=user.external_id,
            name=name,
            display_name=user.display_name,
            nick_name=user.nick_name,
            profile_url=user.profile_url,
            title=user.title,
            user_type=user.user_type,
            preferred_language=user.preferred_language,
            locale=user.locale,
            timezone=user.timezone,
            active=user.active,
            emails=emails or None,
            phone_numbers=phone_numbers or None,
            ims=ims or None,
            photos=photos or None,
            addresses=addresses or None,
            entitlements=entitlements or None,
            roles=roles or None,
            x509_certificates=x509_certificates or None,
            groups=groups or None,
            urn_ietf_params_scim_schemas_extension_enterprise_2_0_User=enterprise_ext,
            meta=meta
        )
    
    @staticmethod
    async def _update_schemas(user: User, schema_uri: str):
        """Update the user's schemas array when a fully qualified attribute is used"""
        # This is handled at the response level, not stored in the database
        # The schemas are determined by which extensions have data
        pass
    
    @staticmethod
    async def _apply_patch_with_parsed_path(
        app_id: str, user: User, op: str, parsed_path, value: Any, op_index: int
    ):
        """Apply a patch operation using a parsed SCIM path"""
        attribute = parsed_path.attribute
        filter_expr = parsed_path.filter_expr
        sub_attribute = parsed_path.sub_attribute
        
        # Handle operations on multi-valued attributes with filters
        if filter_expr:
            await UserService._apply_patch_filtered(
                app_id, user, op, attribute, filter_expr, sub_attribute, value
            )
        elif sub_attribute:
            # Handle nested attributes like name.givenName
            await UserService._apply_patch_nested(
                app_id, user, op, attribute, sub_attribute, value
            )
        else:
            # Simple attribute
            await UserService._apply_patch_attribute(
                app_id, user, op, attribute, value
            )
    
    @staticmethod
    async def _apply_patch_filtered(
        app_id: str, user: User, op: str, attribute: str, filter_expr: str, 
        sub_attribute: Optional[str], value: Any
    ):
        """Apply patch operation to filtered multi-valued attributes"""
        # Map attribute names to model relationships
        multi_valued_map = {
            "emails": (UserEmail, "emails"),
            "phoneNumbers": (UserPhoneNumber, "phone_numbers"),
            "ims": (UserIM, "ims"),
            "photos": (UserPhoto, "photos"),
            "addresses": (UserAddress, "addresses"),
            "entitlements": (UserEntitlement, "entitlements"),
            "roles": (UserRole, "roles"),
            "x509Certificates": (UserX509Certificate, "x509_certificates"),
        }
        
        if attribute not in multi_valued_map:
            raise ValueError(f"Attribute '{attribute}' does not support filters")
        
        model_class, relation_name = multi_valued_map[attribute]
        
        # Get all items of this type
        items = await getattr(user, relation_name).all()
        
        # Convert to dictionaries for filtering
        item_dicts = []
        for item in items:
            item_dict = {
                "value": getattr(item, "value", None),
                "type": getattr(item, "type", None),
                "display": getattr(item, "display", None),
                "primary": None,
                "_db_item": item
            }
            
            # Handle primary field based on model
            if hasattr(item, "primary_email"):
                item_dict["primary"] = item.primary_email
            elif hasattr(item, "primary_phone"):
                item_dict["primary"] = item.primary_phone
            elif hasattr(item, "primary_im"):
                item_dict["primary"] = item.primary_im
            elif hasattr(item, "primary_photo"):
                item_dict["primary"] = item.primary_photo
            elif hasattr(item, "primary_entitlement"):
                item_dict["primary"] = item.primary_entitlement
            elif hasattr(item, "primary_role"):
                item_dict["primary"] = item.primary_role
            elif hasattr(item, "primary_certificate"):
                item_dict["primary"] = item.primary_certificate
            elif hasattr(item, "primary_address"):
                item_dict["primary"] = item.primary_address
                
            item_dicts.append(item_dict)
        
        # Find matching items
        matching_items = find_matching_items(item_dicts, filter_expr)
        
        if op == "remove":
            # Remove matching items
            for item_dict in matching_items:
                await item_dict["_db_item"].delete()
        elif op == "replace" or op == "add":
            if sub_attribute:
                # Update sub-attribute of matching items
                for item_dict in matching_items:
                    db_item = item_dict["_db_item"]
                    if sub_attribute == "primary":
                        await UserService._set_primary(db_item, value, model_class, user, app_id)
                    else:
                        setattr(db_item, sub_attribute, value)
                        await db_item.save()
            else:
                # Replace the entire matching items
                for item_dict in matching_items:
                    await item_dict["_db_item"].delete()
                
                # Add new value
                if value:
                    await UserService._create_multi_valued_item(app_id, user, model_class, value)
    
    @staticmethod
    async def _apply_patch_nested(
        app_id: str, user: User, op: str, attribute: str, sub_attribute: str, value: Any
    ):
        """Apply patch operation to nested attributes like name.givenName"""
        if attribute == "name":
            name_field_map = {
                'formatted': 'name_formatted',
                'familyName': 'name_family_name',
                'givenName': 'name_given_name',
                'middleName': 'name_middle_name',
                'honorificPrefix': 'name_honorific_prefix',
                'honorificSuffix': 'name_honorific_suffix',
            }
            
            if sub_attribute in name_field_map:
                field_name = name_field_map[sub_attribute]
                if op == "replace" or op == "add":
                    setattr(user, field_name, value)
                elif op == "remove":
                    setattr(user, field_name, None)
            else:
                raise ValueError(f"Unknown sub-attribute '{sub_attribute}' for 'name'")
        else:
            # Try as simple attribute with dot notation preserved
            await UserService._apply_patch_simple(app_id, user, op, f"{attribute}.{sub_attribute}", value)
    
    @staticmethod
    async def _apply_patch_attribute(app_id: str, user: User, op: str, attribute: str, value: Any):
        """Apply patch operation to a simple attribute"""
        await UserService._apply_patch_simple(app_id, user, op, attribute, value)
    
    @staticmethod
    async def _set_primary(db_item, is_primary: bool, model_class, user, app_id: str):
        """Set primary flag and ensure only one item is primary"""
        if not is_primary:
            # Just set to false
            if hasattr(db_item, "primary_email"):
                db_item.primary_email = False
            elif hasattr(db_item, "primary_phone"):
                db_item.primary_phone = False
            elif hasattr(db_item, "primary_im"):
                db_item.primary_im = False
            elif hasattr(db_item, "primary_photo"):
                db_item.primary_photo = False
            elif hasattr(db_item, "primary_entitlement"):
                db_item.primary_entitlement = False
            elif hasattr(db_item, "primary_role"):
                db_item.primary_role = False
            elif hasattr(db_item, "primary_certificate"):
                db_item.primary_certificate = False
            elif hasattr(db_item, "primary_address"):
                db_item.primary_address = False
            await db_item.save()
            return
        
        # Setting to true - first set all others to false
        all_items = await model_class.filter(app_id=app_id, user=user).all()
        for item in all_items:
            if item.id != db_item.id:
                if hasattr(item, "primary_email"):
                    item.primary_email = False
                elif hasattr(item, "primary_phone"):
                    item.primary_phone = False
                elif hasattr(item, "primary_im"):
                    item.primary_im = False
                elif hasattr(item, "primary_photo"):
                    item.primary_photo = False
                elif hasattr(item, "primary_entitlement"):
                    item.primary_entitlement = False
                elif hasattr(item, "primary_role"):
                    item.primary_role = False
                elif hasattr(item, "primary_certificate"):
                    item.primary_certificate = False
                elif hasattr(item, "primary_address"):
                    item.primary_address = False
                await item.save()
        
        # Now set this one to true
        if hasattr(db_item, "primary_email"):
            db_item.primary_email = True
        elif hasattr(db_item, "primary_phone"):
            db_item.primary_phone = True
        elif hasattr(db_item, "primary_im"):
            db_item.primary_im = True
        elif hasattr(db_item, "primary_photo"):
            db_item.primary_photo = True
        elif hasattr(db_item, "primary_entitlement"):
            db_item.primary_entitlement = True
        elif hasattr(db_item, "primary_role"):
            db_item.primary_role = True
        elif hasattr(db_item, "primary_certificate"):
            db_item.primary_certificate = True
        elif hasattr(db_item, "primary_address"):
            db_item.primary_address = True
        await db_item.save()