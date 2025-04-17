"""Dropbox entity schemas."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import Field

from airweave.platform.entities._base import ChunkEntity, FileEntity


class DropboxAccountEntity(ChunkEntity):
    """Schema for Dropbox account-level entities based on the Dropbox API.

    REQUIRED fields from ChunkEntity (must be provided):
    - entity_id: ID of the entity this represents in the source
    - breadcrumbs: List of breadcrumbs for this entity (empty for top-level accounts)

    OPTIONAL fields from ChunkEntity (automatically populated if available):
    - Other inherited fields from ChunkEntity
    """

    # Core identification fields
    account_id: str = Field(..., description="The user's unique Dropbox ID")

    # Name information
    name: str = Field(..., description="Name for display representing the user's Dropbox account")
    abbreviated_name: Optional[str] = Field(
        None, description="Abbreviated form of the person's name (typically initials)"
    )
    familiar_name: Optional[str] = Field(
        None, description="Locale-dependent name (usually given name in US)"
    )
    given_name: Optional[str] = Field(None, description="Also known as first name")
    surname: Optional[str] = Field(None, description="Also known as last name or family name")

    # Account status and details
    email: Optional[str] = Field(None, description="The user's email address")
    email_verified: bool = Field(
        False, description="Whether the user has verified their email address"
    )
    disabled: bool = Field(False, description="Whether the user has been disabled")

    # Account type and relationships
    account_type: Optional[str] = Field(
        None, description="Type of account (basic, pro, business, etc.)"
    )
    is_teammate: bool = Field(
        False, description="Whether this user is a teammate of the current user"
    )
    is_paired: bool = Field(
        False, description="Whether the user has both personal and work accounts linked"
    )
    team_member_id: Optional[str] = Field(
        None, description="The user's unique team member ID (if part of a team)"
    )

    # Regional and language settings
    locale: Optional[str] = Field(
        None, description="The language that the user specified (IETF language tag)"
    )
    country: Optional[str] = Field(
        None, description="The user's two-letter country code (ISO 3166-1)"
    )

    # URLs and external references
    profile_photo_url: Optional[str] = Field(None, description="URL for the profile photo")
    referral_link: Optional[str] = Field(None, description="The user's referral link")

    # Quota information
    space_used: Optional[int] = Field(None, description="The user's total space usage in bytes")
    space_allocated: Optional[int] = Field(
        None, description="The user's total space allocation in bytes"
    )

    # Team information
    team_info: Optional[Dict] = Field(
        None, description="Information about the team if user is a member"
    )

    # Root information
    root_info: Optional[Dict] = Field(
        None, description="Information about the user's root namespace"
    )


class DropboxFolderEntity(ChunkEntity):
    """Schema for Dropbox folder entities matching the Dropbox API.

    REQUIRED fields from ChunkEntity (must be provided):
    - entity_id: ID of the entity this represents in the source
    - breadcrumbs: List of breadcrumbs for this entity

    OPTIONAL fields from ChunkEntity (automatically populated if available):
    - Other inherited fields from ChunkEntity
    """

    # REQUIRED Core identification fields
    folder_id: str = Field(..., description="Unique identifier for the folder")
    name: str = Field(..., description="The name of the folder (last path component)")

    # OPTIONAL Path information
    path_lower: Optional[str] = Field(None, description="Lowercase full path starting with slash")
    path_display: Optional[str] = Field(None, description="Display path with proper casing")

    # OPTIONAL Complete sharing info object
    sharing_info: Optional[Dict] = Field(None, description="Sharing information for the folder")

    # OPTIONAL Key sharing fields extracted for convenience (from sharing_info)
    read_only: bool = Field(False, description="Whether the folder is read-only")
    traverse_only: bool = Field(False, description="Whether the folder can only be traversed")
    no_access: bool = Field(False, description="Whether the folder cannot be accessed")

    # OPTIONAL Custom properties/tags
    property_groups: Optional[List[Dict]] = Field(None, description="Custom properties and tags")


class DropboxFileEntity(FileEntity):
    """Schema for Dropbox file entities matching the Dropbox API.

    REQUIRED fields from FileEntity (must be provided):
    - file_id: ID of the file in the source system
    - name: Name of the file
    - download_url: URL to download the file

    OPTIONAL fields from FileEntity (automatically populated if available):
    - Other inherited fields from ChunkEntity
    """

    # Dropbox-specific fields - ALL OPTIONAL
    path_lower: Optional[str] = Field(None, description="Lowercase full path in Dropbox")
    path_display: Optional[str] = Field(None, description="Display path with proper casing")
    rev: Optional[str] = Field(None, description="Unique identifier for the file revision")
    client_modified: Optional[datetime] = Field(
        None, description="When file was modified by client"
    )
    server_modified: Optional[datetime] = Field(
        None, description="When file was modified on server"
    )
    is_downloadable: bool = Field(True, description="Whether file can be downloaded directly")
    content_hash: Optional[str] = Field(
        None, description="Dropbox content hash for integrity checks"
    )

    # Additional optional fields
    sharing_info: Optional[Dict] = Field(None, description="Sharing information for the file")
    has_explicit_shared_members: Optional[bool] = Field(
        None, description="Whether file has explicit shared members"
    )
