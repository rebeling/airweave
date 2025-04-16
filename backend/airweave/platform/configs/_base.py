"""Base config class."""

from typing import Optional, get_args, get_origin

from pydantic import BaseModel


class BaseConfig(BaseModel):
    """Base config class."""

    pass


class ConfigField(BaseModel):
    """Config field model."""

    name: str
    title: str
    description: Optional[str] = None
    type: str


_type_map = {str: "string", int: "number", float: "number", bool: "boolean"}


class Fields(BaseModel):
    """Fields model."""

    fields: list[ConfigField]

    @classmethod
    def from_config_class(cls, config_class: type[BaseConfig]) -> "Fields":
        """Create fields from config class."""
        fields = []
        for field_name, field_info in config_class.model_fields.items():
            # Get the actual type, handling Optional types
            annotation = field_info.annotation
            if get_origin(annotation) is Optional:
                annotation = get_args(annotation)[0]

            # Get the base type if it's a Field
            if hasattr(annotation, "__origin__"):
                annotation = annotation.__origin__

            # Map the type to string representation
            type_str = _type_map.get(annotation, "string")  # Default to string if type not found

            fields.append(
                ConfigField(
                    name=field_name,
                    title=field_info.title or field_name,
                    description=field_info.description,
                    type=type_str,
                )
            )
        return Fields(fields=fields)
