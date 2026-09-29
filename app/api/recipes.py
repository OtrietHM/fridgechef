from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app import services

router = APIRouter(prefix="/recipes", tags=["Recipes"])


class RecipeRequest(BaseModel):
    ingredients: list[str] = Field(..., min_length=1, examples=[["tomato", "egg", "spinach"]])
    preference: str | None = Field(None, examples=["vegetarian"])


@router.post("/generate")
async def create_recipe(req: RecipeRequest):
    try:
        return await services.generate_refined_recipe(req.ingredients, req.preference)
    except services.MissingAPIKeyError:
        raise HTTPException(503, "Server is missing OPENAI_API_KEY.")
    except services.RecipeGenerationError:
        raise HTTPException(502, "The AI service failed. Please try again.")
    except services.RecipeValidationError as exc:
        raise HTTPException(422, f"Could not produce a valid recipe: {exc}")


@router.post("/vision/detect")
async def detect_ingredients(file: UploadFile = File(...)):
    # Placeholder for Phase 2 Computer Vision module
    return {"detected_ingredients": ["tomato", "egg", "spinach"]}
