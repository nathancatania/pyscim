from typing import Optional
from fastapi import APIRouter, Response, Header, Path, Body, status, Request
from scim.schemas import GroupRequest, GroupResponse, ListResponse, PatchRequest, ErrorResponse, SCIMSchemaUri
from scim.services.group_service import GroupService
from scim.dependencies import AuthUser, Pagination, FilterParam, SortParams, AttributesFilter, RequestId, AppId
from scim.exceptions import PreconditionFailed, InvalidPatch
from scim.utils import validate_etag, logger, AttributeFilter
from scim.config import settings

router = APIRouter(tags=["Groups"])


@router.post("/Groups", response_model=GroupResponse, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED, responses={400: {"model": ErrorResponse, "description": "Invalid request"}, 409: {"model": ErrorResponse, "description": "Group already exists"}})
async def create_group(
    request: Request,
    group_data: GroupRequest = Body(...),
    app_id: AppId = None,
    auth_user: AuthUser = None,
    request_id: RequestId = None,
) -> GroupResponse:
    logger.info(f"Creating group: {group_data.display_name} (request_id: {request_id})")

    # Debug log the raw JSON payload before Pydantic validation
    if settings.debug or settings.log_level.upper() == "DEBUG":
        try:
            raw_body = await request.body()
            logger.debug(f"Raw User POST request body (request_id: {request_id}): {raw_body.decode('utf-8')}")
        except Exception as e:
            logger.warning(f"Failed to log raw request body: {e}")

    # Debug log the full JSON payload
    if settings.debug or settings.log_level.upper() == "DEBUG":
        logger.debug(f"Group POST payload (request_id: {request_id}): {group_data.model_dump_json(indent=2)}")

    group = await GroupService.create_group(app_id, group_data)
    return group


@router.get("/Groups/{group_id}", response_model=GroupResponse, response_model_exclude_none=True, responses={404: {"model": ErrorResponse, "description": "Group not found"}})
async def get_group(
    group_id: str = Path(..., description="Group ID"),
    attributes: AttributesFilter = None,
    app_id: AppId = None,
    auth_user: AuthUser = None,
) -> GroupResponse:
    logger.info(f"Getting group: {group_id}")
    group = await GroupService.get_group(app_id, group_id)

    # Apply attribute filtering if requested
    if attributes and (attributes[0] or attributes[1]):
        group_dict = group.model_dump(by_alias=True, mode="json", exclude_none=True)
        filtered_dict = AttributeFilter.filter_resource(
            group_dict,
            attributes=attributes[0],
            excluded_attributes=attributes[1]
        )
        return filtered_dict

    return group


@router.get("/Groups", response_model=ListResponse, response_model_exclude_none=True, responses={400: {"model": ErrorResponse, "description": "Invalid filter"}})
async def list_groups(
    pagination: Pagination = None,
    filter_param: FilterParam = None,
    sort_params: SortParams = None,
    attributes: AttributesFilter = None,
    app_id: AppId = None,
    auth_user: AuthUser = None,
) -> ListResponse:
    logger.info(f"Listing groups (filter: {filter_param}, sort: {sort_params})")

    sort_by, sort_order = sort_params
    groups, total = await GroupService.list_groups(app_id, offset=pagination.offset, limit=pagination.limit, filter_query=filter_param, sort_by=sort_by, sort_order=sort_order)

    # Convert to list response
    resources = [group.model_dump(by_alias=True, mode="json", exclude_none=True) for group in groups]

    # Apply attribute filtering if requested
    if attributes and (attributes[0] or attributes[1]):
        resources = AttributeFilter.filter_list_response(
            resources,
            attributes=attributes[0],
            excluded_attributes=attributes[1]
        )

    return ListResponse(total_results=total, Resources=resources, start_index=pagination.start_index, items_per_page=len(resources))


@router.put("/Groups/{group_id}", response_model=GroupResponse, response_model_exclude_none=True, responses={404: {"model": ErrorResponse, "description": "Group not found"}, 409: {"model": ErrorResponse, "description": "Conflict"}, 412: {"model": ErrorResponse, "description": "Precondition failed"}})
async def replace_group(
    request: Request,
    group_id: str = Path(..., description="Group ID"),
    group_data: GroupRequest = Body(...),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    attributes: AttributesFilter = None,
    app_id: AppId = None,
    auth_user: AuthUser = None,
) -> GroupResponse:
    logger.info(f"Replacing group: {group_id}")

    # Debug log the raw JSON payload before Pydantic validation
    if settings.debug or settings.log_level.upper() == "DEBUG":
        try:
            raw_body = await request.body()
            logger.debug(f"Raw Group PUT request body (request_id:): {raw_body.decode('utf-8')}")
        except Exception as e:
            logger.warning(f"Failed to log raw request body: {e}")

    # Check ETag if provided
    if if_match:
        current_group = await GroupService.get_group(app_id, group_id)
        if not validate_etag(if_match, current_group.meta.version):
            raise PreconditionFailed("ETag mismatch")

    group = await GroupService.update_group(app_id, group_id, group_data)
    
    # Apply attribute filtering if requested
    if attributes and (attributes[0] or attributes[1]):
        group_dict = group.model_dump(by_alias=True, mode="json", exclude_none=True)
        filtered_dict = AttributeFilter.filter_resource(
            group_dict,
            attributes=attributes[0],
            excluded_attributes=attributes[1]
        )
        return filtered_dict
        
    return group


@router.patch("/Groups/{group_id}", response_model=GroupResponse, response_model_exclude_none=True, responses={400: {"model": ErrorResponse, "description": "Invalid patch"}, 404: {"model": ErrorResponse, "description": "Group not found"}, 412: {"model": ErrorResponse, "description": "Precondition failed"}})
async def patch_group(
    request: Request,
    group_id: str = Path(..., description="Group ID"),
    patch_request: PatchRequest = Body(...),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    attributes: AttributesFilter = None,
    app_id: AppId = None,
    auth_user: AuthUser = None,
) -> GroupResponse:
    logger.info(f"Patching group: {group_id}")

    # Debug log the raw JSON payload before Pydantic validation
    if settings.debug or settings.log_level.upper() == "DEBUG":
        try:
            raw_body = await request.body()
            logger.debug(f"Raw Group PATCH request body: {raw_body.decode('utf-8')}")
        except Exception as e:
            logger.warning(f"Failed to log raw request body: {e}")

    # Validate patch request
    if SCIMSchemaUri.PATCH_OP.value not in patch_request.schemas:
        raise InvalidPatch("Invalid schema for PATCH request")

    # Check ETag if provided
    current_group = await GroupService.get_group(app_id, group_id)
    if if_match and not validate_etag(if_match, current_group.meta.version):
        raise PreconditionFailed("ETag mismatch")

    # Apply PATCH operations
    try:
        patched_group = await GroupService.patch_group(app_id, group_id, patch_request.Operations)
        
        # Apply attribute filtering if requested
        if attributes and (attributes[0] or attributes[1]):
            group_dict = patched_group.model_dump(by_alias=True, mode="json", exclude_none=True)
            filtered_dict = AttributeFilter.filter_resource(
                group_dict,
                attributes=attributes[0],
                excluded_attributes=attributes[1]
            )
            return filtered_dict
            
        return patched_group
    except ValueError as e:
        raise InvalidPatch(str(e))
    except Exception as e:
        logger.error(f"Failed to patch group {group_id}: {e}")
        raise InvalidPatch(f"Failed to apply patch: {str(e)}")


@router.delete("/Groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT, responses={404: {"model": ErrorResponse, "description": "Group not found"}})
async def delete_group(
    group_id: str = Path(..., description="Group ID"),
    app_id: AppId = None,
    auth_user: AuthUser = None,
) -> Response:
    logger.info(f"Deleting group: {group_id}")
    await GroupService.delete_group(app_id, group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
