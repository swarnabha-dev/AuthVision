from fastapi import APIRouter, Depends
from .. import config
from ..services.auth import get_current_user

router = APIRouter(prefix="/departments")

@router.get('/list')
def list_departments(user=Depends(get_current_user)):
    """Return list of departments from config."""
    return [{"id": name, "name": name} for name in config.DEPARTMENTS]
