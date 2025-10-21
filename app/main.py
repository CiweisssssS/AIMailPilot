from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router


app = FastAPI(
    title="AI Email Assistant",
    description="Gmail Workspace Add-on Backend API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https://(script\.google\.com|script\.googleusercontent\.com|mail\.google\.com|(?:[\w-]+\.)*replit\.(dev|app))$|^http://localhost:5000$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

app.include_router(router)


@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}


@app.get("/version")
async def version():
    return {"version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
