from os import environ
import uuid
from typing import Dict, Any
from datetime import datetime, timedelta
import pymongo

from fastapi import FastAPI, HTTPException, Depends, status, Response, Cookie
from pydantic import BaseModel, Field

SESSION_LIFETIME_SECONDS = 600
SESSION_CLEANUP_INTERVAL_SECONDS = 60
SESSION_COOKIE_NAME = "session_id"

client = pymongo.MongoClient(
    host=environ["MONGO_HOST"],
    port=int(environ["MONGO_PORT"]),
    username=environ["MONGO_USER"],
    password=environ["MONGO_PASSWORD"]
)

db = client["service"]
users = db["users"]

ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}

class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: str
    password: str = Field(min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class UserProfile(BaseModel):
    username: str
    email: str
    full_name: str | None = None
    bio: str | None = None

class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    bio: str | None = None

app = FastAPI(title="Dummy HTTP Service")

def get_current_user_id(session_token: str = Cookie("", alias=SESSION_COOKIE_NAME)) -> str:
    if session_data := ACTIVE_SESSIONS.get(session_token):
        return session_data["user_id"]

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated or session expired. Please log in.",
    )

@app.post("/register", status_code=status.HTTP_201_CREATED, summary="Create a new user account")
def register_user(user_in: UserIn):

    if users.find_one({'username': user_in.username}):
        raise HTTPException(status_code=400, detail="Username already registered.")
    if users.find_one({'email': user_in.email}):
        raise HTTPException(status_code=400, detail="Email already registered.")

    user_doc = {
        "username": user_in.username,
        "email": user_in.email,
        "password": user_in.password,
        "full_name": None,
        "bio": None,
    }

    user_id = str(users.insert_one(user_doc).inserted_id)

    print(f"User registered: {user_in.username}, ID: {user_id}")
    return {"message": "User registered successfully", "user_id": user_id}


@app.post("/login", summary="Authenticate a user")
def login_user(user_login: UserLogin, response: Response):

    user_data = users.find_one({'username': user_login.username})

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found | invalid data")

    if user_login.password != user_data.get("password"):
        raise HTTPException(status_code=401, detail="Incorrect password")

    user_id = user_data['_id']

    session_token = str(uuid.uuid4())
    expiration_time = datetime.now() + timedelta(seconds=SESSION_LIFETIME_SECONDS)

    ACTIVE_SESSIONS[session_token] = {
        "user_id": user_id,
        "expires_at": expiration_time
    }

    max_age_seconds = int(timedelta(seconds=SESSION_LIFETIME_SECONDS).total_seconds())

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite='lax',
        secure=False,
        max_age=max_age_seconds
    )

    return {"message": "Login successful", "username": user_login.username}


@app.get("/profile", response_model=UserProfile, summary="Retrieve the current user's profile")
def get_profile(current_user_id: str = Depends(get_current_user_id)):

    user_data = users.find_one({'_id': current_user_id})

    if not user_data:
        raise HTTPException(status_code=404, detail="User profile not found")

    return UserProfile(
        username=user_data["username"],
        email=user_data["email"],
        full_name=user_data["full_name"],
        bio=user_data["bio"],
    )


@app.put("/profile", response_model=UserProfile, summary="Update the current user's profile")
def update_profile(
    profile_update: UserProfileUpdate,
    current_user_id: str = Depends(get_current_user_id)
):

    profile_data = {}
    if profile_update.full_name is not None:
        profile_data["full_name"] = profile_update.full_name

    if profile_update.bio is not None:
        profile_data["bio"] = profile_update.bio

    if not profile_data:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    if not users.update_one({'_id': current_user_id}, {"$set": profile_data}):
         raise HTTPException(status_code=404, detail="User profile not found during update.")

    user_data = users.find_one({'_id': current_user_id})

    if not user_data:
        raise HTTPException(status_code=404, detail="User profile not found after update.")

    return UserProfile(
        username=user_data["username"],
        email=user_data["email"],
        full_name=user_data["full_name"],
        bio=user_data["bio"],
    )


@app.get("/backdoor", response_model=UserProfile, summary="Super secret backdoor")
def get_backdoor(username: str):
    user_data = users.find_one({"username": username})
    if not user_data:
        raise HTTPException(status_code=404, detail="User profile not found.")

    return UserProfile(
        username=user_data["username"],
        email=user_data["email"],
        full_name=user_data["full_name"],
        bio=user_data["bio"],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9000,
        workers=8,
        log_level="info"
    )
