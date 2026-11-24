import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from supabase import Client, create_client
from supabase_auth.errors import AuthApiError

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


class Credentials(BaseModel):
    email: str | None = None
    password: str | None = None


@app.post("/auth/signup")
def signup(body: Credentials) -> JSONResponse:
    if not body.email or not body.password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required"},
        )

    try:
        response = supabase.auth.sign_up(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError as error:
        return JSONResponse(status_code=error.status, content={"error": error.message})

    if response.user is None:
        return JSONResponse(status_code=400, content={"error": "Could not create user"})

    return JSONResponse(
        status_code=201,
        content=response.user.model_dump(mode="json"),
    )


@app.post("/auth/login")
def login(body: Credentials) -> JSONResponse:
    if not body.email or not body.password:
        return JSONResponse(
            status_code=400,
            content={"error": "Email and password are required"},
        )

    try:
        response = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid login credentials"},
        )

    if response.session is None:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid login credentials"},
        )

    return JSONResponse(
        status_code=200,
        content={
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
        },
    )


def extract_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    if authorization is None:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    
    return token.strip()


@app.get("/public/info")
def public_info() -> dict[str, str]:
    return {"message": "Welcome stranger! This info is public."}

@app.get("/protected/profile")
def protected_profile(request: Request) -> JSONResponse:
    token = extract_bearer_token(request)
    if token is None:
        return JSONResponse(
            status_code=401,
            content={"error": "Access token required"}
        )

    return JSONResponse(
        status_code=200,
        content={"message": "Token received, not verifiel yet"},
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
