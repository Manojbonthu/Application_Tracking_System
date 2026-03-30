import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import init_db
from api.upload import router as upload_router
from api.analyze import router as analyze_router
from api.results import router as results_router
from api.invitations import router as invitations_router  # ✅ added

load_dotenv()

app = FastAPI(
    title="AI-Powered ATS",
    description="Applicant Tracking System with semantic resume matching",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api", tags=["Upload"])
app.include_router(analyze_router, prefix="/api", tags=["Analyze"])
app.include_router(results_router, prefix="/api", tags=["Results"])
app.include_router(invitations_router, prefix="/api", tags=["Invitations"])  # ✅ added

@app.on_event("startup")
def startup():
    init_db()
    print("✅ ATS Backend started.")

@app.get("/")
def root():
    return {"message": "AI-Powered ATS API is running.", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)