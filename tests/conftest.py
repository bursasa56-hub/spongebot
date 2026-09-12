import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.session import create_engine, init_db, make_session_factory


@pytest_asyncio.fixture
async def engine():
    eng = create_engine(":memory:")
    await init_db(eng)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    maker = make_session_factory(engine)
    async with maker() as s:
        yield s


@pytest_asyncio.fixture(autouse=True)
def anyio_backend():
    return "asyncio"
