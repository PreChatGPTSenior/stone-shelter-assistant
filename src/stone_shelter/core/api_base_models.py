"""Shared configuration for validated API requests and responses."""

from pydantic import BaseModel, ConfigDict


class ApiRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="ignore",
        validate_by_name=True,
        validate_by_alias=True,
    )


class ApiResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        serialize_by_alias=True,
    )
