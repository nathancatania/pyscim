from typing import Optional
from fastapi import APIRouter, Response, Header, Path, Body, status, Request
from scim.schemas import UserRequest, UserResponse, ListResponse, PatchRequest, ErrorResponse, SCIMSchemaUri
from scim.services.user_service import UserService
from scim.dependencies import AuthUser, Pagination, FilterParam, SortParams, AttributesFilter, RequestId, AppId
from scim.exceptions import PreconditionFailed, InvalidPatch
from scim.utils import validate_etag, logger, AttributeFilter
from scim.config import settings

router = APIRouter(tags=["Users"])


@router.post("/Users", response_model=UserResponse, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED, responses={400: {"model": ErrorResponse, "description": "Invalid request"}, 409: {"model": ErrorResponse, "description": "User already exists"}})
async def create_user(
    request: Request,
    user_data: UserRequest = Body(...),
    app_id: AppId = None,
    auth_user: AuthUser = None,
    request_id: RequestId = None,
) -> UserResponse:
    # Debug log the raw JSON payload before Pydantic validation
    if settings.debug or settings.log_level.upper() == "DEBUG":
        try:
            raw_body = await request.body()
            logger.debug(f"Raw User POST request body (request_id: {request_id}): {raw_body.decode('utf-8')}")
        except Exception as e:
            logger.warning(f"Failed to log raw request body: {e}")

    logger.info(f"Creating user: {user_data.user_name} (request_id: {request_id})")

    # Debug log the parsed/validated Pydantic model
    if settings.debug or settings.log_level.upper() == "DEBUG":
        logger.debug(f"User POST request payload (request_id: {request_id}): {user_data.model_dump_json(indent=2)}")

    user = await UserService.create_user(app_id, user_data)

    logger.debug(f"User POST response payload (request_id: {request_id}): {user.model_dump_json(indent=2)}")
    return user


@router.get("/Users/{user_id}", response_model=UserResponse, response_model_exclude_none=True, responses={404: {"model": ErrorResponse, "description": "User not found"}})
async def get_user(
    user_id: str = Path(..., description="User ID"),
    attributes: AttributesFilter = None,
    app_id: AppId = None,
    auth_user: AuthUser = None,
) -> UserResponse:
    logger.info(f"Getting user: {user_id}")
    user = await UserService.get_user(app_id, user_id)

    # Apply attribute filtering if requested
    if attributes and (attributes[0] or attributes[1]):
        user_dict = user.model_dump(by_alias=True, mode="json", exclude_none=True)
        filtered_dict = AttributeFilter.filter_resource(
            user_dict,
            attributes=attributes[0],
            excluded_attributes=attributes[1]
        )
        # Convert back to UserResponse - we need to handle this properly
        # For now, return a dict response which FastAPI will serialize
        return filtered_dict

    logger.debug(f"User GET response payload: {user.model_dump_json(indent=2)}")

    return user


@router.get("/Users", response_model=ListResponse, response_model_exclude_none=True, responses={400: {"model": ErrorResponse, "description": "Invalid filter"}})
async def list_users(
    pagination: Pagination = None,
    filter_param: FilterParam = None,
    sort_params: SortParams = None,
    attributes: AttributesFilter = None,
    app_id: AppId = None,
    auth_user: AuthUser = None,
) -> ListResponse:
    logger.info(f"Listing users (filter: {filter_param}, sort: {sort_params})")

    sort_by, sort_order = sort_params
    users, total = await UserService.list_users(app_id, offset=pagination.offset, limit=pagination.limit, filter_query=filter_param, sort_by=sort_by, sort_order=sort_order)

    # Convert to list response
    resources = [user.model_dump(by_alias=True, mode="json", exclude_none=True) for user in users]

    # Apply attribute filtering if requested
    if attributes and (attributes[0] or attributes[1]):
        resources = AttributeFilter.filter_list_response(
            resources,
            attributes=attributes[0],
            excluded_attributes=attributes[1]
        )

    response = ListResponse(total_results=total, Resources=resources, start_index=pagination.start_index, items_per_page=len(resources))
    logger.debug(f"ListResponse: {response.model_dump_json(indent=2)}")

    return response


@router.put("/Users/{user_id}", response_model=UserResponse, response_model_exclude_none=True, responses={404: {"model": ErrorResponse, "description": "User not found"}, 409: {"model": ErrorResponse, "description": "Conflict"}, 412: {"model": ErrorResponse, "description": "Precondition failed"}})
async def replace_user(
    user_id: str = Path(..., description="User ID"),
    user_data: UserRequest = Body(...),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    attributes: AttributesFilter = None,
    app_id: AppId = None,
    auth_user: AuthUser = None,
) -> UserResponse:
    logger.info(f"Replacing user: {user_id}")

    # Debug log the parsed/validated Pydantic model
    if settings.debug or settings.log_level.upper() == "DEBUG":
        logger.debug(f"User PUT request payload: {user_data.model_dump_json(indent=2)}")

    # Check ETag if provided
    if if_match:
        current_user = await UserService.get_user(app_id, user_id)
        if not validate_etag(if_match, current_user.meta.version):
            raise PreconditionFailed("ETag mismatch")

    user = await UserService.update_user(app_id, user_id, user_data)

    # Apply attribute filtering if requested
    if attributes and (attributes[0] or attributes[1]):
        user_dict = user.model_dump(by_alias=True, mode="json", exclude_none=True)
        filtered_dict = AttributeFilter.filter_resource(
            user_dict,
            attributes=attributes[0],
            excluded_attributes=attributes[1]
        )
        return filtered_dict

    logger.debug(f"User: {user.model_dump_json(indent=2)}")
    return user


@router.patch("/Users/{user_id}", response_model=UserResponse, response_model_exclude_none=True, responses={400: {"model": ErrorResponse, "description": "Invalid patch"}, 404: {"model": ErrorResponse, "description": "User not found"}, 412: {"model": ErrorResponse, "description": "Precondition failed"}})
async def patch_user(
    user_id: str = Path(..., description="User ID"),
    patch_request: PatchRequest = Body(...),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    attributes: AttributesFilter = None,
    app_id: AppId = None,
    auth_user: AuthUser = None,
) -> UserResponse:
    logger.info(f"Patching user: {user_id}")

    # Validate patch request
    if SCIMSchemaUri.PATCH_OP.value not in patch_request.schemas:
        raise InvalidPatch("Invalid schema for PATCH request")

    # Check ETag if provided
    if if_match:
        current_user = await UserService.get_user(app_id, user_id)
        if not validate_etag(if_match, current_user.meta.version):
            raise PreconditionFailed("ETag mismatch")

    # Debug log the parsed/validated Pydantic model
    if settings.debug or settings.log_level.upper() == "DEBUG":
        logger.debug(f"User PATCH request payload: {patch_request.model_dump_json(indent=2)}")

    # Apply patch operations
    try:
        user = await UserService.patch_user(app_id, user_id, patch_request.Operations)
        
        # Apply attribute filtering if requested
        if attributes and (attributes[0] or attributes[1]):
            user_dict = user.model_dump(by_alias=True, mode="json", exclude_none=True)
            filtered_dict = AttributeFilter.filter_resource(
                user_dict,
                attributes=attributes[0],
                excluded_attributes=attributes[1]
            )
            return filtered_dict
            
        logger.debug(f"User PATCH response payload: {user.model_dump_json(indent=2)}")
        return user
    except ValueError as e:
        raise InvalidPatch(str(e))


@router.delete("/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, responses={404: {"model": ErrorResponse, "description": "User not found"}})
async def delete_user(
    user_id: str = Path(..., description="User ID"),
    app_id: AppId = None,
    auth_user: AuthUser = None,
) -> Response:
    logger.info(f"Deleting user: {user_id}")
    await UserService.delete_user(app_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
