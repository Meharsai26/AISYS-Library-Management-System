from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.foundation import (
    Permission, Role, RolePermission,
    UserAccount, UserRole,
)

ROLE_PERMISSIONS = {
    "ADMIN": {
        "admin:read", "admin:users", "admin:roles",
        "audit:read", "catalog:read", "catalog:write",
        "member:read", "member:write",
        "circulation:write", "report:read",
    },
    "LIBRARIAN": {
        "catalog:read", "member:read", "member:write",
        "circulation:write", "tag:read", "report:read",
    },
    "CATALOGUER": {
        "catalog:read", "catalog:write", "tag:write",
        "tag:read",
    },
    "INVENTORY": {
        "inventory:read", "inventory:write",
        "tag:read", "gate:read",
    },
    "PATRON": {"catalog:read"},
}

def seed():
    with SessionLocal() as db:
        roles = {}
        for code, permissions in ROLE_PERMISSIONS.items():
            role = db.scalar(select(Role).where(Role.code == code))
            if role is None:
                role = Role(code=code)
                db.add(role)
                db.flush()
            roles[code] = role

            for permission_code in permissions:
                permission = db.get(Permission, permission_code)
                if permission is None:
                    db.add(Permission(code=permission_code))
                    db.flush()

                link = db.get(
                    RolePermission, (role.id, permission_code)
                )
                if link is None:
                    db.add(
                        RolePermission(
                            role_id=role.id,
                            permission_code=permission_code,
                        )
                    )

        db.commit()

        for username, role_code in [
            ("demo_admin", "ADMIN"),
            ("demo_librarian", "LIBRARIAN"),
        ]:
            user = db.scalar(
                select(UserAccount).where(
                    UserAccount.username == username
                )
            )
            if user is not None:
                print(f"{username} already exists; unchanged")
                continue

            password = getpass(f"Enter password for {username}: ")
            if len(password) < 12:
                raise ValueError("Password must be at least 12 characters")

            user = UserAccount(
                username=username,
                password_hash=hash_password(password),
                is_active=True,
            )
            db.add(user)
            db.flush()
            db.add(
                UserRole(user_id=user.id, role_id=roles[role_code].id)
            )
            db.commit()
            print(f"Created synthetic user: {username}")

if __name__ == "__main__":
    seed()
