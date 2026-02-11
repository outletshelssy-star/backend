from fastapi import Depends, HTTPException, status

from app.core.security.dependencies import get_current_active_user
from app.models.enums import UserType
from app.models.user import User


def require_role(*roles: UserType):
    """
    Dependency para restringir acceso por rol.

    Uso:
        Depends(require_role(UserType.admin))
        Depends(require_role(UserType.admin, UserType.superadmin))
    """

    def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.user_type not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_user

    return role_checker
