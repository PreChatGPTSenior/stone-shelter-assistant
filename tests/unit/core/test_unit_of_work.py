from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from stone_shelter_assistant.core.unit_of_work import SqlAlchemyUnitOfWork, UnitOfWork


@pytest.mark.asyncio
async def test_unit_of_work_rolls_back_without_commit() -> None:
    session = AsyncMock(spec=AsyncSession)
    session_factory = Mock(return_value=session)
    uow: UnitOfWork = SqlAlchemyUnitOfWork(session_factory)

    async with uow as work:
        assert work is uow

    session_factory.assert_called_once_with()
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()
    session.close.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_unit_of_work_commits_explicitly() -> None:
    session = AsyncMock(spec=AsyncSession)
    session_factory = Mock(return_value=session)
    uow: UnitOfWork = SqlAlchemyUnitOfWork(session_factory)

    async with uow:
        await uow.commit()
        session.commit.assert_awaited_once_with()
        session.close.assert_not_awaited()

    session.commit.assert_awaited_once_with()
    session.rollback.assert_awaited_once_with()
    session.close.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_unit_of_work_rolls_back_on_exception() -> None:
    session = AsyncMock(spec=AsyncSession)
    session_factory = Mock(return_value=session)
    uow: UnitOfWork = SqlAlchemyUnitOfWork(session_factory)

    with pytest.raises(ValueError, match="Registration failed"):
        async with uow:
            raise ValueError("Registration failed")

    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()
    session.close.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_unit_of_work_closes_session_when_rollback_fails() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.rollback.side_effect = RuntimeError("Rollback failed")
    session_factory = Mock(return_value=session)
    uow: UnitOfWork = SqlAlchemyUnitOfWork(session_factory)

    with pytest.raises(RuntimeError, match="Rollback failed"):
        async with uow:
            pass

    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()
    session.close.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_unit_of_work_session_is_available_only_inside_context() -> None:
    session = AsyncMock(spec=AsyncSession)
    session_factory = Mock(return_value=session)
    uow = SqlAlchemyUnitOfWork(session_factory)

    with pytest.raises(RuntimeError, match="Unit of work is not active"):
        _ = uow.session

    async with uow:
        assert uow.session is session

    with pytest.raises(RuntimeError, match="Unit of work is not active"):
        _ = uow.session


@pytest.mark.asyncio
async def test_unit_of_work_rejects_commit_outside_context() -> None:
    session = AsyncMock(spec=AsyncSession)
    session_factory = Mock(return_value=session)
    uow: UnitOfWork = SqlAlchemyUnitOfWork(session_factory)

    with pytest.raises(RuntimeError, match="Unit of work is not active"):
        await uow.commit()

    async with uow:
        pass

    with pytest.raises(RuntimeError, match="Unit of work is not active"):
        await uow.commit()

    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_unit_of_work_cleans_up_when_commit_fails() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.commit.side_effect = RuntimeError("Commit failed")
    session_factory = Mock(return_value=session)
    uow: UnitOfWork = SqlAlchemyUnitOfWork(session_factory)

    with pytest.raises(RuntimeError, match="Commit failed"):
        async with uow:
            await uow.commit()

    session.commit.assert_awaited_once_with()
    session.rollback.assert_awaited_once_with()
    session.close.assert_awaited_once_with()
