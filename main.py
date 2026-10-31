import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import config
from api.routes_project import router as project_router

app = FastAPI(
    title="Full Auto Story Animation Studio",
    description="Tam Otomatik Hikâyeli 2D Animasyon Video Oluşturma Platformu (0 TL Maliyet)",
    version="1.0.0-stage2",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(project_router)

app.mount("/exports", StaticFiles(directory=str(config.EXPORTS_DIR)), name="exports")
app.mount("/css", StaticFiles(directory=str(config.FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(config.FRONTEND_DIR / "js")), name="js")

@app.get("/")
async def serve_mobile_studio():
    index_file = config.FRONTEND_DIR / "index.html"
    return FileResponse(
        str(index_file),
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
