from fastapi import APIRouter, Request, UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.gateway import (
    build_create_input,
    create_gateway_job,
    get_gateway_job,
    parse_preferences,
    retry_gateway_job,
)
from app.schemas import CreateResearchJobResponse, ResearchJobResponse

router = APIRouter(prefix="/api")


@router.post("/research-jobs", response_model=CreateResearchJobResponse, response_model_by_alias=True)
async def create_research_job_route(request: Request) -> CreateResearchJobResponse:
    content_type = request.headers.get("content-type", "")
    image_file: UploadFile | None = None

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        image_candidate = form.get("image") or form.get("file")
        if isinstance(image_candidate, StarletteUploadFile):
            image_file = image_candidate
        create_input = build_create_input(
            {
                "inputType": form.get("inputType"),
                "textDescription": form.get("textDescription"),
                "researchPreferences": parse_preferences(form.get("researchPreferences")),
            }
        )
    else:
        body = await request.json()
        body["researchPreferences"] = parse_preferences(body.get("researchPreferences"))
        create_input = build_create_input(body)

    return await create_gateway_job(create_input=create_input, image_file=image_file)


@router.get("/research-jobs/{job_id}", response_model=ResearchJobResponse, response_model_by_alias=True)
async def get_research_job_route(job_id: str) -> ResearchJobResponse:
    return await get_gateway_job(job_id)


@router.post("/research-jobs/{job_id}/retry", response_model=ResearchJobResponse, response_model_by_alias=True)
async def retry_research_job_route(job_id: str) -> ResearchJobResponse:
    return await retry_gateway_job(job_id)
