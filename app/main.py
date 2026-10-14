from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title="Gerencia de Costos de Produccion",
    description="Backend para analisis de insumos y costos de produccion.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    return {"message": "Bienvenido a Gerencia de Costos API", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
