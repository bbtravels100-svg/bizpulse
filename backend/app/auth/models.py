from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Core user attributes shared across schemas."""
    email: str = Field(..., description="Unique email address")
    name: str = Field(..., description="Full display name")
    role: str = Field(default="Operations Manager", description="Primary organizational role")
    department: str = Field(default="Operations", description="Department / team name")


class UserResponse(UserBase):
    """
    Public user representation.
    CRITICAL: Never includes password_hash or internal secrets.
    """
    id: str
    is_active: bool
    created_at: str
    updated_at: str


class UserLoginRequest(BaseModel):
    """Login payload with email and password."""
    email: str
    password: str


class UserRegisterRequest(BaseModel):
    """
    Controlled user provisioning payload.
    Requires provisioning_key if open demo registration is disabled.
    """
    email: str
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    name: str
    role: Optional[str] = "Operations Manager"
    department: Optional[str] = "Operations"
    provisioning_key: Optional[str] = None


class TokenResponse(BaseModel):
    """JWT access token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserResponse


class MessageResponse(BaseModel):
    """Generic status message response."""
    message: str
    status: str = "success"
