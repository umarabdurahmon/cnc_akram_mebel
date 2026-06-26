from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.security import verify_init_data
from app.db.session import get_db
from app.models.employee import Employee
from app.repositories.employee import get_by_telegram_id


def get_current_employee(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> Employee:
    if not authorization.startswith("tma "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    try:
        data = verify_init_data(authorization[4:])
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid initData")
    if data.user is None:
        raise HTTPException(status_code=401, detail="No user in initData")
    emp = get_by_telegram_id(db, data.user.id)
    if emp is None:
        raise HTTPException(status_code=403, detail="Employee not found")
    if not emp.is_active:
        raise HTTPException(status_code=403, detail="Employee is inactive")
    return emp
