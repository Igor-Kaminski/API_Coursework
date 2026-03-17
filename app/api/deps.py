from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.security import AuthContext, Role, require_roles
from app.db.session import get_db_session

DBSession = Annotated[Session, Depends(get_db_session)]
AdminUser = Annotated[AuthContext, Depends(require_roles(Role.admin))]
OperatorOrAdmin = Annotated[AuthContext, Depends(require_roles(Role.admin, Role.operator))]
