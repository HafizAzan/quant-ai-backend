from fastapi import APIRouter

from app.schemas.auth import APIResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=APIResponse[dict[str, str]])
async def health() -> APIResponse[dict[str, str]]:
    return APIResponse(data={"status": "ok", "service": "quantai-api"})
