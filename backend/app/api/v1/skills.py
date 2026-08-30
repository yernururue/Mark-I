from fastapi import APIRouter, Depends

from app.api.contracts import error_responses
from app.dependencies import get_current_user_id, get_skill_service
from app.models.skill import SkillsResponse
from app.services.skill_service import SkillService

router = APIRouter(tags=["Skills"])

@router.get("/skills", response_model=SkillsResponse, responses=error_responses(401, 422), operation_id="getSkills")
async def get_skills(
    uid: str = Depends(get_current_user_id),
    skill_service: SkillService = Depends(get_skill_service),
):
    """
    Get all skill scores for the authenticated user.
    """
    skills = skill_service.get_skills(uid)
    return SkillsResponse(skills=skills)
