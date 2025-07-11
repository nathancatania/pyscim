from typing import List, Optional, Union, Any
from tortoise.exceptions import IntegrityError
from tortoise.transactions import atomic
from scim.models import Group, GroupMember, User, UserEmail
from scim.schemas import (
    GroupRequest, GroupResponse, GroupMember as GroupMemberSchema,
    Meta, ResourceType, SCIMSchemaUri
)
from scim.exceptions import ResourceNotFound, ResourceAlreadyExists
from scim.utils import generate_etag, SCIMFilterParser, logger, parse_scim_path, find_matching_items
from scim.config import settings


class GroupService:
    @staticmethod
    async def _resolve_user(identifier: str, app_id: str) -> Optional[User]:
        """
        Resolve a user by multiple lookup strategies within an application.
        
        Attempts resolution in the following order:
        1. UUID - Direct UUID lookup
        2. Username - Exact username match
        3. Email - Check email records
        4. Employee Number - Enterprise user employee number
        5. External ID - Identity provider's external ID
        
        This method handles various identifier formats from identity providers
        like Okta, which may send any of these identifier types.
        
        Args:
            identifier: The user reference (UUID, username, email, employee number, or external ID)
            app_id: The application ID
            
        Returns:
            The resolved User object, or None if not found
        """
        if not identifier:
            return None
        
        # 1. Try to parse as UUID first
        try:
            import uuid
            user_uuid = uuid.UUID(identifier)
            # Verify the user exists
            user = await User.filter(app_id=app_id, id=user_uuid).first()
            if user:
                logger.debug(f"Resolved group member by UUID: {identifier}")
                return user
        except ValueError:
            # Not a UUID, continue with other lookup methods
            pass
        
        # 2. Try username lookup
        logger.debug(f"Member identifier '{identifier}' is not a UUID, attempting username lookup")
        user = await User.filter(app_id=app_id, user_name=identifier).first()
        if user:
            logger.debug(f"Found group member by username: {identifier} -> {user.id}")
            return user
        
        # 3. Try email lookup
        logger.debug(f"Attempting email lookup for: {identifier}")
        # Look for users who have this email
        email_match = await UserEmail.filter(
            app_id=app_id, 
            value=identifier.lower()  # Emails are stored lowercase
        ).first()
        if email_match:
            user = await email_match.user
            logger.debug(f"Found group member by email: {identifier} -> {user.id}")
            return user
        
        # 4. Try employee number lookup
        logger.debug(f"Attempting employee number lookup for: {identifier}")
        user = await User.filter(app_id=app_id, employee_number=identifier).first()
        if user:
            logger.debug(f"Found group member by employee number: {identifier} -> {user.id}")
            return user
        
        # 5. Try external_id lookup
        logger.debug(f"Attempting external_id lookup for: {identifier}")
        user = await User.filter(app_id=app_id, external_id=identifier).first()
        if user:
            logger.debug(f"Found group member by external_id: {identifier} -> {user.id}")
            return user
        
        # No match found with any method
        logger.warning(f"Group member reference '{identifier}' not found using any lookup method in app {app_id}")
        return None
    
    @staticmethod
    async def _resolve_group(identifier: str, app_id: str) -> Optional[Group]:
        """
        Resolve a group by ID or external ID within an application.
        First tries to find by ID (UUID), then by external_id if not found.
        """
        # Try to find by ID first (check if it's a valid UUID format)
        try:
            # This will raise ValueError if not a valid UUID format
            import uuid
            uuid.UUID(identifier)
            group = await Group.filter(id=identifier, app_id=app_id).first()
            if group:
                return group
        except ValueError:
            # Not a UUID format, continue to check external_id
            pass
        
        # Try to find by external_id
        group = await Group.filter(external_id=identifier, app_id=app_id).first()
        return group
    
    @staticmethod
    @atomic()
    async def create_group(app_id: str, group_data: GroupRequest) -> GroupResponse:
        try:
            # Create group
            group = await Group.create(
                app_id=app_id,
                display_name=group_data.display_name,
                external_id=group_data.external_id,
            )
            
            # Add members if provided
            if group_data.members:
                for member_data in group_data.members:
                    # Determine if it's a user or group member
                    member_type = member_data.type or "User"
                    
                    if member_type.lower() == "user":
                        user = await GroupService._resolve_user(member_data.value, app_id)
                        if user:
                            await GroupMember.create(
                                app_id=app_id,
                                group=group,
                                user=user,
                                display=member_data.display or user.display_name,
                                type="User"
                            )
                        else:
                            logger.warning(f"User with identifier '{member_data.value}' not found, skipping member")
                    elif member_type.lower() == "group":
                        nested_group = await GroupService._resolve_group(member_data.value, app_id)
                        if nested_group:
                            await GroupMember.create(
                                app_id=app_id,
                                group=group,
                                nested_group=nested_group,
                                display=member_data.display or nested_group.display_name,
                                type="Group"
                            )
                        else:
                            logger.warning(f"Group with identifier '{member_data.value}' not found, skipping member")
            
            # Generate ETag
            group.etag = generate_etag(group)
            await group.save()
            
            return await GroupService._to_response(group)
            
        except IntegrityError as e:
            if "display_name" in str(e):
                raise ResourceAlreadyExists("Group", "displayName", group_data.display_name)
            elif "external_id" in str(e):
                raise ResourceAlreadyExists("Group", "externalId", group_data.external_id)
            raise
    
    @staticmethod
    async def get_group(app_id: str, group_id: str) -> GroupResponse:
        group = await Group.filter(id=group_id, app_id=app_id).prefetch_related(
            "members", "members__user", "members__nested_group"
        ).first()
        
        if not group:
            raise ResourceNotFound("Group", group_id)
        
        return await GroupService._to_response(group)
    
    @staticmethod
    @atomic()
    async def update_group(app_id: str, group_id: str, group_data: GroupRequest) -> GroupResponse:
        group = await Group.filter(id=group_id, app_id=app_id).first()
        if not group:
            raise ResourceNotFound("Group", group_id)
        
        # Update basic fields
        group.display_name = group_data.display_name
        group.external_id = group_data.external_id
        
        # Update members (delete and recreate for simplicity)
        await GroupMember.filter(group=group, app_id=app_id).delete()
        
        if group_data.members:
            for member_data in group_data.members:
                member_type = member_data.type or "User"
                
                if member_type.lower() == "user":
                    user = await GroupService._resolve_user(member_data.value, app_id)
                    if user:
                        await GroupMember.create(
                            app_id=app_id,
                            group=group,
                            user=user,
                            display=member_data.display or user.display_name,
                            type="User"
                        )
                    else:
                        logger.warning(f"User with identifier '{member_data.value}' not found, skipping member")
                elif member_type.lower() == "group":
                    nested_group = await GroupService._resolve_group(member_data.value, app_id)
                    if nested_group:
                        await GroupMember.create(
                            app_id=app_id,
                            group=group,
                            nested_group=nested_group,
                            display=member_data.display or nested_group.display_name,
                            type="Group"
                        )
                    else:
                        logger.warning(f"Group with identifier '{member_data.value}' not found, skipping member")
        
        # Generate new ETag
        group.etag = generate_etag(group)
        await group.save()
        
        return await GroupService._to_response(group)
    
    @staticmethod
    async def delete_group(app_id: str, group_id: str) -> None:
        group = await Group.filter(id=group_id, app_id=app_id).first()
        if not group:
            raise ResourceNotFound("Group", group_id)
        
        await group.delete()
    
    @staticmethod
    async def list_groups(
        app_id: str,
        offset: int = 0,
        limit: int = 100,
        filter_query: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "ascending"
    ) -> tuple[List[GroupResponse], int]:
        query = Group.filter(app_id=app_id)
        
        # Apply filter if provided
        if filter_query:
            try:
                parser = SCIMFilterParser(resource_type='Group')
                filter_q = parser.parse(filter_query)
                query = query.filter(filter_q)
            except ValueError as e:
                # Per RFC 7644, invalid filters should return 400 Bad Request
                logger.warning(f"Invalid SCIM filter: {filter_query} - {str(e)}")
                raise ValueError(f"Invalid filter: {str(e)}")
        
        # Get total count after filtering
        total_count = await query.count()
        
        # Apply sorting
        if sort_by:
            # Map SCIM attributes to model fields for sorting
            sort_field_map = {
                'displayName': 'display_name',
                'externalId': 'external_id',
                'meta.created': 'created',
                'meta.lastModified': 'modified',
            }
            sort_field = sort_field_map.get(sort_by, sort_by)
            order_prefix = "-" if sort_order == "descending" else ""
            query = query.order_by(f"{order_prefix}{sort_field}")
        else:
            query = query.order_by("created")
        
        # Apply pagination
        groups = await query.offset(offset).limit(limit).prefetch_related(
            "members", "members__user", "members__nested_group"
        )
        
        responses = []
        for group in groups:
            responses.append(await GroupService._to_response(group))
        
        return responses, total_count
    
    @staticmethod
    async def _to_response(group: Group) -> GroupResponse:
        # Build members list
        members = []
        # Ensure members are loaded with their relations
        group_members = await group.members.all().prefetch_related("user", "nested_group")
        
        for member in group_members:
            if member.user_id:
                # Ensure user is loaded
                if not hasattr(member, 'user') or member.user is None:
                    member.user = await User.filter(id=member.user_id, app_id=group.app_id).first()
                if member.user:
                    ref = f"{settings.api_prefix}/Users/{member.user.id}"
                    value = str(member.user.id)
                    display = member.display or member.user.display_name
                else:
                    continue  # Skip if user not found
            elif member.nested_group_id:
                # Ensure nested_group is loaded
                if not hasattr(member, 'nested_group') or member.nested_group is None:
                    member.nested_group = await Group.filter(id=member.nested_group_id, app_id=group.app_id).first()
                if member.nested_group:
                    ref = f"{settings.api_prefix}/Groups/{member.nested_group.id}"
                    value = str(member.nested_group.id)
                    display = member.display or member.nested_group.display_name
                else:
                    continue  # Skip if group not found
            else:
                continue  # Skip invalid members
            
            members.append(GroupMemberSchema(
                value=value,
                ref=ref,
                display=display,
                type=member.type
            ))
        
        # Build meta
        meta = Meta(
            resource_type=ResourceType.GROUP,
            created=group.created,
            last_modified=group.modified,
            location=f"{settings.api_prefix}/Groups/{group.id}",
            version=group.etag
        )
        
        return GroupResponse(
            schemas=[SCIMSchemaUri.GROUP.value],
            id=str(group.id),
            display_name=group.display_name,
            external_id=group.external_id,
            members=members or None,
            meta=meta
        )
    
    @staticmethod
    @atomic()
    async def patch_group(app_id: str, group_id: str, operations: List) -> GroupResponse:
        """Apply PATCH operations to a group as per RFC 7644 Section 3.5.2"""
        logger.debug(f"patch_group: Starting patch for group {group_id} in app {app_id}")
        
        group = await Group.filter(app_id=app_id, id=group_id).prefetch_related(
            "members", "members__user", "members__nested_group"
        ).first()
        
        if not group:
            raise ResourceNotFound("Group", group_id)
        
        logger.debug(f"patch_group: Group loaded with {await group.members.all().count()} members")
        
        for idx, operation in enumerate(operations):
            op = operation.op.lower()
            path = operation.path
            value = operation.value
            
            logger.debug(f"patch_group: Processing operation {idx + 1} - op: {op}, path: {path}, value: {value}")
            
            # Enforce path requirements per RFC 7644
            if op == "remove" and not path:
                raise ValueError(f"Operation {idx + 1}: 'path' is required for 'remove' operations")
            
            # Handle operations without path
            if not path:
                if op == "replace" and isinstance(value, dict):
                    await GroupService._apply_patch_replace_all(app_id, group, value)
                elif op == "add" and isinstance(value, dict):
                    # Add operation without path adds/replaces attributes
                    await GroupService._apply_patch_replace_all(app_id, group, value)
                else:
                    raise ValueError(f"Operation {idx + 1}: Invalid operation '{op}' without path")
                continue
            
            # Parse the SCIM path
            try:
                parsed_path = parse_scim_path(path)
                logger.debug(f"patch_group: Parsed path - {parsed_path}")
                
                # Apply the operation based on the parsed path
                await GroupService._apply_patch_with_parsed_path(
                    app_id, group, op, parsed_path, value, idx
                )
                
            except ValueError as e:
                raise ValueError(f"Operation {idx + 1}: Invalid path '{path}' - {str(e)}")
            except Exception as e:
                raise ValueError(f"Operation {idx + 1} failed: {str(e)}")
        
        # Generate new ETag and save
        group.etag = generate_etag(group)
        await group.save()
        
        logger.debug(f"patch_group: Patch completed successfully for group {group_id}")
        
        return await GroupService._to_response(group)
    
    @staticmethod
    async def _apply_patch_replace_all(app_id: str, group: Group, values: dict):
        """Apply replace operation to multiple attributes"""
        if "displayName" in values:
            group.display_name = values["displayName"]
        if "externalId" in values:
            group.external_id = values["externalId"]
        if "members" in values:
            await GroupService._patch_members(app_id, group, "replace", values["members"])
    
    @staticmethod
    async def _patch_simple_attribute(group: Group, op: str, attribute: str, value):
        """Apply patch operation to a simple attribute"""
        if op == "replace" or op == "add":
            setattr(group, attribute, value)
        elif op == "remove":
            setattr(group, attribute, None)
        else:
            raise ValueError(f"Invalid operation '{op}' for attribute '{attribute}'")
    
    @staticmethod
    async def _patch_members(app_id: str, group: Group, op: str, value):
        """Handle patch operations for group members"""
        logger.debug(f"_patch_members: op={op}, value={value}")
        
        if op == "add":
            if isinstance(value, list):
                for member_data in value:
                    await GroupService._add_member(app_id, group, member_data)
            else:
                await GroupService._add_member(app_id, group, value)
        
        elif op == "remove":
            if value is None:
                # Remove all members
                await GroupMember.filter(app_id=app_id, group=group).delete()
            elif isinstance(value, list):
                # Remove specific members
                for member_data in value:
                    if isinstance(member_data, dict) and "value" in member_data:
                        await GroupService._remove_member(app_id, group, member_data["value"])
                    elif isinstance(member_data, str):
                        await GroupService._remove_member(app_id, group, member_data)
            else:
                if isinstance(value, dict) and "value" in value:
                    await GroupService._remove_member(app_id, group, value["value"])
                elif isinstance(value, str):
                    await GroupService._remove_member(app_id, group, value)
        
        elif op == "replace":
            # Replace all members
            await GroupMember.filter(app_id=app_id, group=group).delete()
            if isinstance(value, list):
                for member_data in value:
                    await GroupService._add_member(app_id, group, member_data)
            elif value is not None:
                await GroupService._add_member(app_id, group, value)
    
    @staticmethod
    async def _add_member(app_id: str, group: Group, member_data: Union[str, dict]):
        """Add a single member to the group"""
        if isinstance(member_data, str):
            # Simple string value
            member_value = member_data
            member_type = "User"
            member_display = None
        elif isinstance(member_data, dict):
            member_value = member_data.get("value")
            member_type = member_data.get("type", "User")
            member_display = member_data.get("display")
        else:
            logger.warning(f"Invalid member data type: {type(member_data)}")
            return
        
        if not member_value:
            logger.warning("Member value is empty, skipping")
            return
        
        logger.debug(f"_add_member: Adding member {member_value} of type {member_type}")
        
        # Check if member already exists
        if member_type.lower() == "user":
            # First resolve the user to get the actual user object
            user = await GroupService._resolve_user(member_value, app_id)
            if not user:
                logger.warning(f"User with identifier '{member_value}' not found")
                return
            
            existing = await GroupMember.filter(
                app_id=app_id,
                group=group,
                user=user
            ).exists()
            if existing:
                logger.debug(f"User {user.id} is already a member of group {group.id}")
                return
            
            # Create the membership
            await GroupMember.create(
                app_id=app_id,
                group=group,
                user=user,
                display=member_display or user.display_name,
                type="User"
            )
            logger.info(f"Added user {user.id} to group {group.id}")
        
        elif member_type.lower() == "group":
            # First resolve the group to get the actual group object
            nested_group = await GroupService._resolve_group(member_value, app_id)
            if not nested_group:
                logger.warning(f"Group with identifier '{member_value}' not found")
                return
            
            existing = await GroupMember.filter(
                app_id=app_id,
                group=group,
                nested_group=nested_group
            ).exists()
            if existing:
                logger.debug(f"Group {nested_group.id} is already a member of group {group.id}")
                return
            
            # Create the membership
            await GroupMember.create(
                app_id=app_id,
                group=group,
                nested_group=nested_group,
                display=member_display or nested_group.display_name,
                type="Group"
            )
            logger.info(f"Added group {nested_group.id} to group {group.id}")
    
    @staticmethod
    async def _remove_member(app_id: str, group: Group, member_value: str):
        """Remove a member from the group"""
        if not member_value:
            return
        
        logger.debug(f"_remove_member: Removing member {member_value} from group {group.id}")
        
        # Try to remove as user first
        user = await GroupService._resolve_user(member_value, app_id)
        if user:
            deleted = await GroupMember.filter(
                app_id=app_id,
                group=group,
                user=user
            ).delete()
            if deleted:
                logger.info(f"Removed user {user.id} from group {group.id}")
                return
        
        # Try to remove as group
        nested_group = await GroupService._resolve_group(member_value, app_id)
        if nested_group:
            deleted = await GroupMember.filter(
                app_id=app_id,
                group=group,
                nested_group=nested_group
            ).delete()
            if deleted:
                logger.info(f"Removed group {nested_group.id} from group {group.id}")
                return
        
        logger.warning(f"Member '{member_value}' not found in group {group.id}")
    
    @staticmethod
    async def _apply_patch_with_parsed_path(
        app_id: str, group: Group, op: str, parsed_path, value: Any, op_index: int
    ):
        """Apply a patch operation using a parsed SCIM path"""
        attribute = parsed_path.attribute
        filter_expr = parsed_path.filter_expr
        sub_attribute = parsed_path.sub_attribute
        
        # Groups have simpler structure than users
        if filter_expr and attribute == "members":
            # Handle members with filters like members[value eq "user-id"]
            await GroupService._apply_patch_members_filtered(
                app_id, group, op, filter_expr, sub_attribute, value
            )
        elif attribute.lower() == "displayname":
            await GroupService._patch_simple_attribute(group, op, "display_name", value)
        elif attribute.lower() == "externalid":
            await GroupService._patch_simple_attribute(group, op, "external_id", value)
        elif attribute.lower() == "members":
            await GroupService._patch_members(app_id, group, op, value)
        else:
            raise ValueError(f"Unknown attribute '{attribute}' for groups")
    
    @staticmethod
    async def _apply_patch_members_filtered(
        app_id: str, group: Group, op: str, filter_expr: str, 
        sub_attribute: Optional[str], value: Any
    ):
        """Apply patch operation to filtered members like members[value eq 'user-id']"""
        # Get all members
        members = await group.members.all().prefetch_related("user", "nested_group")
        
        # Convert to dictionaries for filtering
        member_dicts = []
        for member in members:
            member_dict = {
                "value": str(member.user.id) if member.user else str(member.nested_group.id),
                "type": member.type,
                "display": member.display,
                "$ref": None,  # Could be added if needed
                "_db_item": member
            }
            member_dicts.append(member_dict)
        
        # Find matching members
        matching_members = find_matching_items(member_dicts, filter_expr)
        
        if op == "remove":
            # Remove matching members
            for member_dict in matching_members:
                await member_dict["_db_item"].delete()
                logger.info(f"Removed member from group {group.id} based on filter: {filter_expr}")
        elif op == "replace" or op == "add":
            if sub_attribute:
                # Update sub-attribute of matching members (e.g., display name)
                for member_dict in matching_members:
                    db_item = member_dict["_db_item"]
                    if sub_attribute == "display":
                        db_item.display = value
                        await db_item.save()
                    else:
                        raise ValueError(f"Cannot update sub-attribute '{sub_attribute}' of members")
            else:
                # Replace matching members - remove old and add new
                for member_dict in matching_members:
                    await member_dict["_db_item"].delete()
                
                # Add new member
                if value:
                    await GroupService._add_member(app_id, group, value)