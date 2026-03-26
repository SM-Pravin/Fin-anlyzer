from fastapi import APIRouter, HTTPException, status, Depends
from src.database.connection import get_database
from src.core.security import verify_password, create_access_token
from src.models.schemas import LoginRequest, TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    db = await get_database()
    user = await db["users"].find_one({"username": body.username})

    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    token = create_access_token(username=user["username"], role=user["role"])
    return TokenResponse(access_token=token, role=user["role"])
