from fastapi import FastAPI

from app.api.recipes import router as recipes_router

app = FastAPI(title="FridgeChef")
app.include_router(recipes_router)


@app.get("/")
async def health():
    return {"status": "ok"}
