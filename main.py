from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.extract import router


app = FastAPI(title="Invoice Extractor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
