from app.core.config import get_settings
from app.core.security import Role


def resolve_api_role(api_key: str | None) -> Role:
    if not api_key:
        raise ValueError("api_key is required for this tool")

    settings = get_settings()
    role_lookup = {
        settings.admin_api_key: Role.ADMIN,
        settings.operator_api_key: Role.OPERATOR,
        settings.user_api_key: Role.USER,
    }
    role = role_lookup.get(api_key)
    if role is None:
        raise ValueError("invalid API key")
    return role


def require_api_role(api_key: str | None, *allowed_roles: Role) -> Role:
    role = resolve_api_role(api_key)
    if role not in allowed_roles:
        allowed = ", ".join(sorted(item.value for item in allowed_roles))
        raise ValueError(f"insufficient permissions; expected one of: {allowed}")
    return role
