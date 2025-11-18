"""
OAuth routes for Google authentication
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
import os
import secrets
from urllib.parse import urlencode

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://aimailpilot-api.onrender.com/oauth/google/callback")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

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
async def google_callback(code: str = None, state: str = None, error: str = None):
    """
    Handle Google OAuth callback
    This should exchange the code for tokens and redirect to frontend
    """
    if error:
        # Redirect to frontend with error
        frontend_url = os.getenv("FRONTEND_URL", "https://ai-mail-pilot.vercel.app")
        return RedirectResponse(url=f"{frontend_url}?error={error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    # TODO: Exchange code for tokens
    # For now, redirect back to frontend
    # In production, you would:
    # 1. Exchange code for access_token and refresh_token
    # 2. Store tokens in session/database
    # 3. Set session cookie
    # 4. Redirect to frontend
    
    frontend_url = os.getenv("FRONTEND_URL", "https://ai-mail-pilot.vercel.app")
    return RedirectResponse(url=frontend_url)

