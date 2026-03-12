from fastapi import FastAPI
from routes import query_routes

app = FastAPI(title="Legal AI Backend")

app.include_router(query_routes.router)
