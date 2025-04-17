"""Base CRUD class for public tables."""

from typing import Any, Generic, Optional, Type, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from airweave.db.unit_of_work import UnitOfWork
from airweave.models._base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBaseSystem(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """CRUD base class for system tables.

    Implements CRUD methods without user or organization context.
    """

    def __init__(self, model: Type[ModelType]):
        """CRUD object with default methods for public tables.

        Args:
        ----
            model (Type[ModelType]): The model to be used in the CRUD operations.

        """
        self.model = model

    async def get(self, db: AsyncSession, id: UUID) -> Optional[ModelType]:
        """Get a single object by ID.

        Args:
        ----
            db (AsyncSession): The database session.
            id (UUID): The UUID of the object to get.

        Returns:
        -------
            Optional[ModelType]: The object with the given ID.

        """
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.unique().scalar_one_or_none()

    async def get_by_short_name(self, db: AsyncSession, short_name: str) -> Optional[ModelType]:
        """Get a single object by short name.

        Args:
        ----
            db (AsyncSession): The database session.
            short_name (str): The short name of the object  to get.

        Returns:
        -------
            Optional[ModelType]: The object with the given short name.
        """
        result = await db.execute(select(self.model).where(self.model.short_name == short_name))
        return result.unique().scalar_one_or_none()

    async def get_all(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, disable_limit: bool = True
    ) -> list[ModelType]:
        """Get multiple objects.

        Args:
        ----
            db (AsyncSession): The database session.
            skip (int): The number of objects to skip.
            limit (int): The number of objects to return.
            disable_limit (bool): Disable the limit parameter by default.

        Returns:
        -------
            List[ModelType]: A list of objects.

        """
        query = select(self.model).offset(skip)
        if not disable_limit:
            query = query.limit(limit)

        result = await db.execute(query)
        return list(result.unique().scalars().all())

    async def create(
        self, db: AsyncSession, *, obj_in: CreateSchemaType, uow: UnitOfWork = None
    ) -> ModelType:
        """Create a new object.

        Args:
        ----
            db (AsyncSession): The database session.
            obj_in (CreateSchemaType): The object to create.
            uow (UnitOfWork, optional): Unit of work for transaction control.
                If not provided, auto-commits the transaction.

        Returns:
        -------
            ModelType: The created object.

        """
        if not isinstance(obj_in, dict):
            obj_in = obj_in.model_dump()
        db_obj = self.model(**obj_in)
        db.add(db_obj)

        if uow is None:
            await db.commit()

        return db_obj

    async def create_many(
        self, db: AsyncSession, objs_in: list[CreateSchemaType], uow: UnitOfWork = None
    ) -> list[ModelType]:
        """Create multiple objects.

        Args:
        ----
            db (AsyncSession): The database session.
            objs_in (list[CreateSchemaType]): The objects to create.
            uow (UnitOfWork, optional): Unit of work for transaction control.

        Returns:
        -------
            list[ModelType]: The created objects.

        """
        db_objs = [self.model(**obj_in.model_dump()) for obj_in in objs_in]
        db.add_all(db_objs)

        if uow is None:
            await db.commit()

        return db_objs

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, dict[str, Any]],
        uow: UnitOfWork = None,
    ) -> ModelType:
        """Update an object.

        Args:
        ----
            db (AsyncSession): The database session.
            db_obj (ModelType): The object to update.
            obj_in (Union[UpdateSchemaType, Dict[str, Any]]): The new object data.
            uow (UnitOfWork, optional): Unit of work for transaction control.

        Returns:
        -------
            ModelType: The updated object

        """
        if not isinstance(obj_in, dict):
            obj_in = obj_in.model_dump(exclude_unset=True)

        for key, value in obj_in.items():
            setattr(db_obj, key, value) if hasattr(db_obj, key) else None
        db.add(db_obj)

        if uow is None:
            await db.commit()

        return db_obj

    async def remove(
        self, db: AsyncSession, *, id: UUID, uow: UnitOfWork = None
    ) -> Optional[ModelType]:
        """Delete an object.

        Args:
        ----
            db (AsyncSession): The database session.
            id (UUID): The UUID of the object to delete.
            uow (UnitOfWork, optional): Unit of work for transaction control.

        Returns:
        -------
            Optional[ModelType]: The deleted object.

        """
        result = await db.execute(select(self.model).where(self.model.id == id))
        db_obj = result.unique().scalar_one_or_none()
        if db_obj is None:
            return None

        await db.delete(db_obj)

        if uow is None:
            await db.commit()

        return db_obj

    async def sync(
        self, db: AsyncSession, items: list[CreateSchemaType], unique_field: str = "short_name"
    ) -> None:
        """Sync items with the database."""
        # Create a dictionary of new items by their unique field
        new_items_dict = {getattr(item, unique_field): item for item in items}

        # Get existing items
        result = await db.execute(select(self.model))
        existing_items = result.scalars().all()

        # Update existing items or delete them
        for existing_item in existing_items:
            existing_unique_value = getattr(existing_item, unique_field)
            if existing_unique_value in new_items_dict:
                new_item = new_items_dict.pop(existing_unique_value)

                # Update fields from new item
                for field, value in new_item.model_dump().items():
                    if hasattr(existing_item, field):
                        setattr(existing_item, field, value)

                db.add(existing_item)
            else:
                await db.delete(existing_item)

        # Create new items
        for new_item in new_items_dict.values():
            db_item = self.model(**new_item.model_dump())
            db.add(db_item)

        await db.commit()
