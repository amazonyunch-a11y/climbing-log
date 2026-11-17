from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import get_db
from app.main import app
from app.models.user import User


def mark_email_verified(email: str) -> bool:
    override = app.dependency_overrides[get_db]
    dependency = override()
    db = next(dependency)
    try:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            return False
        user.emailVerifiedAt = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        return True
    finally:
        dependency.close()
