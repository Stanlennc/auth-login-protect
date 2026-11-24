import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from supabase import Client, create_client

load_dotenv()

supabase_url: str | None = os.getenv("SUPABASE_URL")
supabase_key: str | None = os.getenv("SUPABASE_KEY")
port: int = int(os.getenv("PORT", "8000"))

if not supabase_url or not supabase_key:
    raise RuntimeError("Supabase url e Supabase key are not set in the .env file")

supabase: Client = create_client(supabase_url, supabase_key)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server running and connected to Supabase")
    yield

app = FastAPI(lifespan=lifespan)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
