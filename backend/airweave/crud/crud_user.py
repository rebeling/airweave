"""The CRUD operations for the User model."""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from airweave.crud._base import CRUDBase
from airweave.models.user import User
from airweave.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """CRUD operations for the User model."""

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Get a user by email.

        Important: this method is not part of the regular CRUD operations.
        This is a custom method for getting a user by email, that does not
        require a current user. Use responsibly.

        Args:
            db (AsyncSession): The database session.
            email (str): The email of the user to get.

        Returns:
            Optional[User]: The user with the given email.
        """
        result = await db.execute(select(User).where(User.email == email))
        return result.unique().scalar_one_or_none()

    async def get(self, db: AsyncSession, id: UUID, current_user: User) -> Optional[User]:
        """Get a single object by ID.

        Args:
            db (AsyncSession): The database session.
            id (UUID): The UUID of the object to get. Doesn't require strict typing.
            current_user (User): The current user.

        Raises:
            NotImplementedError: This method is not implemented.
        """
        raise NotImplementedError("This method is not implemented.")

    async def get_multi(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
        """Get multiple objects.

        WARNING: This method is not secure and should not be used in production.
        It is only used for MLOps and testing purposes.

        TODO: Implement proper security measures through admin roles.

        Args:
            db (AsyncSession): The database session.
            skip (int): The number of objects to skip.
            limit (int): The number of objects to return.

        Returns:
            list[User]: A list of users.
        """
        result = await db.execute(select(User).offset(skip).limit(limit))
        return list(result.unique().scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Create a new user.

        Also creates a default assistant for the user.
        Rolls back the transaction if either the user or the assistant creation fails.

        Args:
            db (AsyncSession): The database session.
            obj_in (UserCreate): The object to create.

        Returns:
            User: The newly created user.
        """
        # If user doesn't have an organization, create a custom one for them
        if not hasattr(obj_in, "organization_id") or obj_in.organization_id is None:
            from airweave.crud.crud_organization import organization as crud_organization
            from airweave.schemas.organization import OrganizationCreate

            org_name = f"Organization for {obj_in.email}"
            org_in = OrganizationCreate(
                name=org_name, description=f"Auto-created organization for {obj_in.email}"
            )
            org = await crud_organization.create(db, obj_in=org_in)

            # Update the user create object with the new organization
            user_data = obj_in.model_dump()
            user_data["organization_id"] = org.id
            obj_in = UserCreate(**user_data)

        user = await super().create(db, obj_in=obj_in)
        return user

    async def remove(self, db: AsyncSession, *, id: UUID, current_user: User) -> Optional[User]:
        """Remove an object by ID.

        Args:
            db (AsyncSession): The database session.
            id (UUID): The UUID of the object to remove. Doesn't require strict typing.
            current_user (User): The current user.

        Raises:
            NotImplementedError: This method is not implemented.
        """
        raise NotImplementedError("This method is not implemented.")

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: User,
        obj_in: UserUpdate | dict[str, Any],
        current_user: User,
    ) -> User:
        """Update an object.

        Args:
            db (AsyncSession): The database session.
            db_obj (User): The object to update.
            obj_in (UserUpdate | dict[str, Any]): The updated object.
            current_user (User): The current user.

        Raises:
            NotImplementedError: This method is not implemented.
        """
        raise NotImplementedError("This method is not implemented.")


user = CRUDUser(User)
