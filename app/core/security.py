from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.config import get_settings


class Role(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    USER = "user"


@dataclass(frozen=True)
class AuthContext:
    role: Role


def _role_lookup() -> dict[str, Role]:
    settings = get_settings()
    return {
        settings.admin_api_key: Role.ADMIN,
        settings.operator_api_key: Role.OPERATOR,
        settings.user_api_key: Role.USER,
    }


def get_auth_context(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> AuthContext:
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing X-API-Key header",
        )

    role = _role_lookup().get(x_api_key)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid API key",
        )

    return AuthContext(role=role)


def require_roles(*allowed_roles: Role) -> Callable[[AuthContext], AuthContext]:
    def dependency(
        auth: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> AuthContext:
        if auth.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient permissions",
            )
        return auth

    return dependency
