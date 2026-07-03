from sqlalchemy.orm import Session
from app.models.models import AuditLog, User
def audit(db: Session, user: User | None, action: str, entity_type: str, entity_id: str | None, description: str, meta: dict | None = None):
    db.add(AuditLog(user_id=user.id if user else None, action=action, entity_type=entity_type, entity_id=entity_id, description=description, meta=meta or {})); db.commit()
