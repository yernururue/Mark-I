from fastapi import APIRouter, Depends
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.dependencies import get_db, get_current_user_id
from app.models.skill import SkillsResponse
from app.services.skill_service import SkillService

router = APIRouter(tags=["Skills"])

@router.get("/skills", response_model=SkillsResponse)
async def get_skills(
    uid: str = Depends(get_current_user_id),
    db: FirestoreClient = Depends(get_db)
):
    """
    Get all skill scores for the authenticated user.
    """
    skill_service = SkillService(db)
    skills = skill_service.get_skills(uid)
    return SkillsResponse(skills=skills)
