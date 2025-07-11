import pytest
import pytest_asyncio
from tortoise import Tortoise


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(autouse=True)
async def initialize_db():
    # Initialize Tortoise ORM for tests
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["src.scim.models"]},
    )
    await Tortoise.generate_schemas()
    
    yield
    
    await Tortoise.close_connections()