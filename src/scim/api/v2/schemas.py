from fastapi import APIRouter, Path
from scim.schemas import ListResponse, ErrorResponse
from scim.schemas.meta import Schema, SchemaAttribute, AttributeType, Mutability, Returned, Uniqueness
from scim.exceptions import ResourceNotFound

router = APIRouter(tags=["Schemas"])


# Define available schemas
USER_SCHEMA = Schema(
    id="urn:ietf:params:scim:schemas:core:2.0:User",
    name="User",
    description="User Account",
    attributes=[
        SchemaAttribute(
            name="userName",
            type=AttributeType.STRING,
            multi_valued=False,
            description="Unique identifier for the User",
            required=True,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.SERVER
        ),
        SchemaAttribute(
            name="externalId",
            type=AttributeType.STRING,
            multi_valued=False,
            description="An identifier for the user as defined by the provisioning client",
            required=False,
            case_exact=True,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="name",
            type=AttributeType.COMPLEX,
            multi_valued=False,
            description="The components of the user's real name",
            required=False,
            sub_attributes=[
                SchemaAttribute(
                    name="formatted",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="The full name",
                    required=False,
                    case_exact=False,
                    mutability=Mutability.READ_WRITE,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
                SchemaAttribute(
                    name="familyName",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="The family name",
                    required=False,
                    case_exact=False,
                    mutability=Mutability.READ_WRITE,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
                SchemaAttribute(
                    name="givenName",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="The given name",
                    required=False,
                    case_exact=False,
                    mutability=Mutability.READ_WRITE,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
            ],
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT
        ),
        SchemaAttribute(
            name="displayName",
            type=AttributeType.STRING,
            multi_valued=False,
            description="The name of the user, suitable for display to end-users",
            required=False,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="nickName",
            type=AttributeType.STRING,
            multi_valued=False,
            description="The casual way to address the user in real life",
            required=False,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="profileUrl",
            type=AttributeType.REFERENCE,
            multi_valued=False,
            description="A fully qualified URL pointing to a page representing the user's online profile",
            required=False,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="title",
            type=AttributeType.STRING,
            multi_valued=False,
            description="The user's title, such as Vice President",
            required=False,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="userType",
            type=AttributeType.STRING,
            multi_valued=False,
            description="Used to identify the relationship between the organization and the user",
            required=False,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="preferredLanguage",
            type=AttributeType.STRING,
            multi_valued=False,
            description="Indicates the user's preferred written or spoken language",
            required=False,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="locale",
            type=AttributeType.STRING,
            multi_valued=False,
            description="Used to indicate the User's default location for purposes of localizing items",
            required=False,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="timezone",
            type=AttributeType.STRING,
            multi_valued=False,
            description="The User's time zone in the 'Olson' time zone database format",
            required=False,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="active",
            type=AttributeType.BOOLEAN,
            multi_valued=False,
            description="A Boolean value indicating the user's administrative status",
            required=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT
        ),
        SchemaAttribute(
            name="password",
            type=AttributeType.STRING,
            multi_valued=False,
            description="The user's cleartext password",
            required=False,
            case_exact=False,
            mutability=Mutability.WRITE_ONLY,
            returned=Returned.NEVER,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="emails",
            type=AttributeType.COMPLEX,
            multi_valued=True,
            description="Email addresses for the user",
            required=False,
            sub_attributes=[
                SchemaAttribute(
                    name="value",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="Email address",
                    required=True,
                    case_exact=False,
                    mutability=Mutability.READ_WRITE,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
                SchemaAttribute(
                    name="type",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="Type of email address",
                    required=False,
                    canonical_values=["work", "home", "other"],
                    case_exact=False,
                    mutability=Mutability.READ_WRITE,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
                SchemaAttribute(
                    name="primary",
                    type=AttributeType.BOOLEAN,
                    multi_valued=False,
                    description="Primary email indicator",
                    required=False,
                    mutability=Mutability.READ_WRITE,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
            ],
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT
        ),
        SchemaAttribute(
            name="phoneNumbers",
            type=AttributeType.COMPLEX,
            multi_valued=True,
            description="Phone numbers for the User",
            required=False,
            sub_attributes=[
                SchemaAttribute(
                    name="value",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="Phone number",
                    required=True,
                    case_exact=False,
                    mutability=Mutability.READ_WRITE,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
                SchemaAttribute(
                    name="type",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="Type of phone number",
                    required=False,
                    canonical_values=["work", "home", "mobile", "fax", "pager", "other"],
                    case_exact=False,
                    mutability=Mutability.READ_WRITE,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
                SchemaAttribute(
                    name="primary",
                    type=AttributeType.BOOLEAN,
                    multi_valued=False,
                    description="Primary phone indicator",
                    required=False,
                    mutability=Mutability.READ_WRITE,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
            ],
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT
        ),
        SchemaAttribute(
            name="groups",
            type=AttributeType.COMPLEX,
            multi_valued=True,
            description="A list of groups to which the user belongs",
            required=False,
            sub_attributes=[
                SchemaAttribute(
                    name="value",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="The identifier of the group",
                    required=True,
                    case_exact=False,
                    mutability=Mutability.READ_ONLY,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
                SchemaAttribute(
                    name="$ref",
                    type=AttributeType.REFERENCE,
                    multi_valued=False,
                    description="The URI of the group resource",
                    required=False,
                    case_exact=False,
                    mutability=Mutability.READ_ONLY,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE,
                    reference_types=["Group"]
                ),
                SchemaAttribute(
                    name="display",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="A human-readable name for the group",
                    required=False,
                    case_exact=False,
                    mutability=Mutability.READ_ONLY,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
                SchemaAttribute(
                    name="type",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="A label indicating the relationship between the member and the group",
                    required=False,
                    canonical_values=["direct", "indirect"],
                    case_exact=False,
                    mutability=Mutability.READ_ONLY,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
            ],
            mutability=Mutability.READ_ONLY,
            returned=Returned.DEFAULT
        ),
    ],
    meta={
        "resourceType": "Schema",
        "location": "/scim/v2/Schemas/urn:ietf:params:scim:schemas:core:2.0:User"
    }
)

GROUP_SCHEMA = Schema(
    id="urn:ietf:params:scim:schemas:core:2.0:Group",
    name="Group",
    description="Group",
    attributes=[
        SchemaAttribute(
            name="displayName",
            type=AttributeType.STRING,
            multi_valued=False,
            description="Human-readable name for the Group",
            required=True,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.SERVER
        ),
        SchemaAttribute(
            name="externalId",
            type=AttributeType.STRING,
            multi_valued=False,
            description="An identifier for the group as defined by the provisioning client",
            required=False,
            case_exact=True,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="members",
            type=AttributeType.COMPLEX,
            multi_valued=True,
            description="A list of members of the Group",
            required=False,
            sub_attributes=[
                SchemaAttribute(
                    name="value",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="Identifier of the member",
                    required=True,
                    case_exact=False,
                    mutability=Mutability.IMMUTABLE,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
                SchemaAttribute(
                    name="$ref",
                    type=AttributeType.REFERENCE,
                    multi_valued=False,
                    description="The URI of the member resource",
                    required=False,
                    case_exact=False,
                    mutability=Mutability.IMMUTABLE,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE,
                    reference_types=["User", "Group"]
                ),
                SchemaAttribute(
                    name="type",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="The type of member",
                    required=False,
                    canonical_values=["User", "Group"],
                    case_exact=False,
                    mutability=Mutability.IMMUTABLE,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
                SchemaAttribute(
                    name="display",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="A human-readable name for the member",
                    required=False,
                    case_exact=False,
                    mutability=Mutability.READ_ONLY,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
            ],
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT
        ),
    ],
    meta={
        "resourceType": "Schema",
        "location": "/scim/v2/Schemas/urn:ietf:params:scim:schemas:core:2.0:Group"
    }
)

ENTERPRISE_USER_SCHEMA = Schema(
    id="urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
    name="EnterpriseUser",
    description="Enterprise User",
    attributes=[
        SchemaAttribute(
            name="employeeNumber",
            type=AttributeType.STRING,
            multi_valued=False,
            description="Numeric or alphanumeric identifier assigned to a person",
            required=False,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="costCenter",
            type=AttributeType.STRING,
            multi_valued=False,
            description="Identifies the cost center",
            required=False,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="organization",
            type=AttributeType.STRING,
            multi_valued=False,
            description="Identifies the organization",
            required=False,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="division",
            type=AttributeType.STRING,
            multi_valued=False,
            description="Identifies the division",
            required=False,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="department",
            type=AttributeType.STRING,
            multi_valued=False,
            description="Identifies the department",
            required=False,
            case_exact=False,
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT,
            uniqueness=Uniqueness.NONE
        ),
        SchemaAttribute(
            name="manager",
            type=AttributeType.COMPLEX,
            multi_valued=False,
            description="The user's manager",
            required=False,
            sub_attributes=[
                SchemaAttribute(
                    name="value",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="Manager identifier",
                    required=False,
                    case_exact=False,
                    mutability=Mutability.READ_WRITE,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
                SchemaAttribute(
                    name="$ref",
                    type=AttributeType.REFERENCE,
                    multi_valued=False,
                    description="Manager URI",
                    required=False,
                    case_exact=False,
                    mutability=Mutability.READ_WRITE,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE,
                    reference_types=["User"]
                ),
                SchemaAttribute(
                    name="displayName",
                    type=AttributeType.STRING,
                    multi_valued=False,
                    description="Manager display name",
                    required=False,
                    case_exact=False,
                    mutability=Mutability.READ_ONLY,
                    returned=Returned.DEFAULT,
                    uniqueness=Uniqueness.NONE
                ),
            ],
            mutability=Mutability.READ_WRITE,
            returned=Returned.DEFAULT
        ),
    ],
    meta={
        "resourceType": "Schema",
        "location": "/scim/v2/Schemas/urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
    }
)

SCHEMAS = {
    USER_SCHEMA.id: USER_SCHEMA,
    GROUP_SCHEMA.id: GROUP_SCHEMA,
    ENTERPRISE_USER_SCHEMA.id: ENTERPRISE_USER_SCHEMA,
}


@router.get(
    "/Schemas",
    response_model=ListResponse,
    response_model_exclude_none=True,
    name="List Schemas"
)
async def list_schemas() -> ListResponse:
    schemas = list(SCHEMAS.values())
    resources = [schema.model_dump(by_alias=True, exclude_none=True) for schema in schemas]
    
    return ListResponse(
        total_results=len(resources),
        Resources=resources,
        start_index=1,
        items_per_page=len(resources)
    )


@router.get(
    "/Schemas/{schema_id}",
    response_model=Schema,
    response_model_exclude_none=True,
    responses={
        404: {"model": ErrorResponse, "description": "Schema not found"}
    },
    name="Get Schema"
)
async def get_schema(
    schema_id: str = Path(..., description="Schema ID")
) -> Schema:
    schema = SCHEMAS.get(schema_id)
    if not schema:
        raise ResourceNotFound("Schema", schema_id)
    
    return schema