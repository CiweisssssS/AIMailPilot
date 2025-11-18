from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://ai-mail-pilot.vercel.app",
]

app = FastAPI(
    title="AI Email Assistant",
    description="Gmail Workspace Add-on Backend API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health_check():
    return {"ok": True}


@app.get("/version")
async def version():
    return {"version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
