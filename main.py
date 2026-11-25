import os
from contextlib import asynccontextmanager
from dataclasses import dataclass

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from supabase import Client, create_client
from supabase_auth.errors import AuthApiError, AuthError

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

class AuthFailure(Exception):
    def __init__(self, message: str) -> None:
        self.message = message

@app.exception_handler(AuthFailure)
def auth_failure_handler(request: Request, exc: AuthFailure) -> JSONResponse:
    return JSONResponse(status_code=401, content={"error": exc.message})

@dataclass
class CurrentUser:
    id: str
    email: str | None
    created_at: str
    token: str

def require_user(request: Request) -> CurrentUser:
    token = extract_bearer_token(request)
    if token is None:
        raise AuthFailure("Access token required")

    try:
        user_response = supabase.auth.get_user(token)
    except AuthError:
        raise AuthFailure("Invalid or expired token")

    if user_response is None or user_response.user is None:
        raise AuthFailure("Invalid or expired token")

    user = user_response.user
    return CurrentUser(
        id=user.id,
        email=user.email,
        created_at=user.created_at.isoformat(),
        token=token,
    )


@app.get("/protected/profile")
def protected_profile(current: CurrentUser = Depends(require_user)) -> dict[str, str] | None:
    return {
            "id": current.id,
            "email": current.email,
            "created_at": current.created_at,
    }

@app.get("/protected/dashboard")
def protected_dashboard(current: CurrentUser = Depends(require_user)) -> dict[str, str]:
    return {"message": f"Welcome back, {current.email}"}

@app.post("/auth/logout", status_code=204)
def logout(current: CurrentUser = Depends(require_user)) -> Response:
    try:
        supabase.auth.admin.sign_out(current.token)
    except AuthError:
        raise AuthFailure("Invalid or expired token")

    return Response(status_code=204)
    

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
