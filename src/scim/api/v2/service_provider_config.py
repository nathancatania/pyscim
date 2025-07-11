from fastapi import APIRouter
from scim.schemas.meta import ServiceProviderConfig
from scim.config import settings

router = APIRouter(tags=["ServiceProviderConfig"])


@router.get(
    "/ServiceProviderConfig",
    response_model=ServiceProviderConfig,
    response_model_exclude_none=True,
    name="Get Service Provider Configuration"
)
async def get_service_provider_config() -> ServiceProviderConfig:
    return ServiceProviderConfig(
        documentation_uri="https://example.com/scim/docs",
        patch={
            "supported": True
        },
        bulk={
            "supported": False,
            "maxOperations": 1000,
            "maxPayloadSize": 1048576
        },
        filter={
            "supported": True,
            "maxResults": settings.max_page_size
        },
        change_password={
            "supported": True
        },
        sort={
            "supported": True
        },
        etag={
            "supported": True
        },
        authentication_schemes=[
            {
                "type": "oauthbearertoken",
                "name": "OAuth Bearer Token",
                "description": "Authentication scheme using the OAuth Bearer Token Standard",
                "specUri": "http://www.rfc-editor.org/info/rfc6750",
                "documentationUri": "https://example.com/scim/docs/auth"
            }
        ],
        meta={
            "location": f"{settings.api_prefix}/ServiceProviderConfig",
            "resourceType": "ServiceProviderConfig",
            "created": "2024-01-01T00:00:00Z",
            "lastModified": "2024-01-01T00:00:00Z"
        }
    )