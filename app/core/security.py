from dataclasses import dataclass
from enum import StrEnum

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import get_settings


class Role(StrEnum):
    admin = "admin"
    operator = "operator"


@dataclass(frozen=True)
class AuthContext:
    role: Role


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_auth_context(api_key: str | None = Security(api_key_header)) -> AuthContext:
    settings = get_settings()

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header.",
        )

    if api_key == settings.admin_api_key:
        return AuthContext(role=Role.admin)

    if api_key == settings.operator_api_key:
        return AuthContext(role=Role.operator)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key.",
    )


def require_roles(*roles: Role):
    def dependency(context: AuthContext = Security(get_auth_context)) -> AuthContext:
        if context.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return context

    return dependency
