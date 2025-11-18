"""
OAuth routes for Google authentication
"""
from fastapi import APIRouter, HTTPException, Request, Response, Request
from fastapi.responses import RedirectResponse
from fastapi import Cookie
from typing import Optional
import os
import secrets
import httpx
from urllib.parse import urlencode
import json

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# Redirect URI should be the Vercel frontend URL which rewrites to backend
# Default to Vercel URL, but can be overridden via env var
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://ai-mail-pilot.vercel.app")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", f"{FRONTEND_URL}/auth/google/callback")
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_urlsafe(32))

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

# In-memory session store (in production, use Redis or database)
# Format: {session_id: {user: {...}, tokens: {...}}}
sessions: dict[str, dict] = {}

def create_session(user_data: dict, tokens: dict) -> str:
    """Create a new session and return session ID"""
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {
        "user": user_data,
        "tokens": tokens
    }
    return session_id

def get_session(session_id: Optional[str]) -> Optional[dict]:
    """Get session data by session ID"""
    if not session_id:
        return None
    return sessions.get(session_id)

def delete_session(session_id: Optional[str]):
    """Delete a session"""
    if session_id and session_id in sessions:
        del sessions[session_id]

@router.get("/oauth/google")
async def google_auth():
    """
    Initiate Google OAuth flow
    Redirects to Google OAuth consent screen
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth credentials not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        )
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Build Google OAuth URL
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    # Redirect to Google OAuth
    return RedirectResponse(url=auth_url)


@router.get("/oauth/google/callback")
async def google_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    response: Response = None
):
    """
    Handle Google OAuth callback
    Exchange code for tokens and create session
    """
    if error:
        frontend_url = os.getenv("FRONTEND_URL", "https://ai-mail-pilot.vercel.app")
        return RedirectResponse(url=f"{frontend_url}?error={error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth credentials not configured"
        )
    
    try:
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code"
                }
            )
            token_response.raise_for_status()
            token_data = token_response.json()
        
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        # Get user info
        async with httpx.AsyncClient() as client:
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_response.raise_for_status()
            user_data = user_response.json()
        
        # Create session
        session_id = create_session(
            user_data={
                "email": user_data.get("email"),
                "name": user_data.get("name"),
                "picture": user_data.get("picture")
            },
            tokens={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": token_data.get("expires_in")
            }
        )
        
        # Set session cookie
        # For cross-origin (Vercel -> Render), we'll use both cookie and URL param
        # as fallback since cross-origin cookies can be tricky
        frontend_url = os.getenv("FRONTEND_URL", "https://ai-mail-pilot.vercel.app")
        
        # Redirect with session_id in URL as fallback (frontend will store it)
        redirect_url = f"{frontend_url}?session_id={session_id}&auth=success"
        response = RedirectResponse(url=redirect_url)
        
        # Also set cookie (may not work cross-origin, but try anyway)
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=True,
            samesite="none",  # Required for cross-origin
            max_age=60 * 60 * 24 * 7,  # 7 days
            path="/"
        )
        return response
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete OAuth: {str(e)}")


@router.get("/api/auth/status")
async def auth_status(
    request: Request,
    session_id: Optional[str] = Cookie(None)
):
    """
    Check authentication status
    Returns user info if authenticated, otherwise returns authenticated: false
    Accepts session_id from cookie or query parameter
    """
    # Try cookie first, then query param
    session_id_param = request.query_params.get("session_id")
    actual_session_id = session_id or session_id_param
    session = get_session(actual_session_id)
    
    if session and session.get("user"):
        return {
            "authenticated": True,
            "user": session["user"]
        }
    else:
        return {
            "authenticated": False
        }


@router.post("/api/auth/logout")
async def logout(session_id: Optional[str] = Cookie(None)):
    """
    Logout and clear session
    """
    delete_session(session_id)
    
    # Return response with cookie cleared
    from fastapi.responses import JSONResponse
    response = JSONResponse({"success": True})
    response.delete_cookie("session_id")
    return response

