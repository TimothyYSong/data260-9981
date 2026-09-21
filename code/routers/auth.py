import time
from pathlib import Path

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND


# Create a router object
# This behaves like a mini FastAPI app
router = APIRouter()

# Configure Jinja2 templates directory
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# Hardcoded credentials for demo purposes only
# In real applications, credentials come from a database
VALID_USERNAME = "admin"
VALID_PASSWORD = "password"

IDLE_TIMEOUT_SECONDS = 30


def get_active_user(request: Request):
    user = request.session.get("user")
    last_activity = request.session.get("last_activity")

    if not user or last_activity is None:
        return None

    current_time = time.time()

    if current_time - last_activity > IDLE_TIMEOUT_SECONDS:
        request.session.clear()
        return None

    request.session["last_activity"] = current_time
    return user


@router.get("/")
def home(request: Request):
    """
    Home page route.

    - Checks if a user is logged in using the session
    - Passes user info to the template
    """
    user = request.session.get("user")

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "user": user
        }
    )


@router.get("/login")
def login_page(
    request: Request,
    error: str | None = None,
    expired: str | None = None
):
    user = request.session.get("user")

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "user": user,
            "error": error,
            "expired": expired
        }
    )


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Handles login form submission.

    - Reads username and password from the form
    - Validates credentials
    - Stores user info in session if valid
    """
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        request.session["user"] = username
        request.session["last_activity"] = time.time()

        return RedirectResponse(
            url="/dashboard",
            status_code=HTTP_302_FOUND
        )

    return RedirectResponse(
        url="/login?error=1",
        status_code=HTTP_302_FOUND
    )


@router.get("/dashboard")
def dashboard(request: Request):
    """
    Protected route.

    - Only accessible if user is logged in
    - Redirects to login page if session is missing
    """
    user = get_active_user(request)

    # If user is not logged in, block access
    if not user:
        return RedirectResponse(
            url="/login?expired=1",
            status_code=HTTP_302_FOUND
        )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": user
        }
    )


@router.get("/logout")
def logout(request: Request):
    """
    Logs the user out.

    - Clears all session data
    - Redirects back to home page
    """
    request.session.clear()

    return RedirectResponse(
        url="/",
        status_code=HTTP_302_FOUND
    )
