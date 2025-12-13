"""
Payment routes - Stripe checkout, webhooks, and portal.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import logging

from app.middleware.auth import require_auth, optional_auth
from app.services.stripe_service import stripe_service
from app.services.supabase_client import supabase_client
from app.config import get_settings
from app.utils.session import get_access_token

logger = logging.getLogger(__name__)
settings = get_settings()
templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/api/payment", tags=["payment"])


@router.get("/upgrade", response_class=HTMLResponse)
async def upgrade_page(request: Request, user_id: str = Depends(require_auth())):
    """
    Display upgrade/pricing page.
    """
    try:
        # Get user profile
        profile_response = supabase_client.table("profiles").select("*").eq("id", user_id).single().execute()
        profile = profile_response.data

        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Get user info for header
        from app.utils.session import get_access_token
        access_token = get_access_token(request)
        user = None

        if access_token:
            try:
                user_response = supabase_client.auth.get_user(access_token)
                if user_response.user:
                    user = {
                        "email": user_response.user.email,
                        "full_name": profile.get("full_name"),
                        "avatar_url": profile.get("avatar_url")
                    }
            except Exception as e:
                logger.warning(f"Failed to get user info: {e}")

        return templates.TemplateResponse(
            "upgrade.html",
            {
                "request": request,
                "user": user,
                "profile": profile
            }
        )

    except Exception as e:
        logger.error(f"Error loading upgrade page: {e}")
        raise HTTPException(status_code=500, detail="Failed to load upgrade page")


@router.post("/create-checkout")
async def create_checkout_session(
    request: Request,
    user_id: str = Depends(require_auth())
):
    """
    Create a Stripe checkout session for Pro subscription.
    """
    try:
        # Get user email
        access_token = get_access_token(request)
        if not access_token:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_response = supabase_client.auth.get_user(access_token)
        if not user_response.user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_email = user_response.user.email

        # Get base URL for redirect
        base_url = str(request.base_url).rstrip('/')

        # Create checkout session
        session_data = stripe_service.create_checkout_session(
            user_id=user_id,
            user_email=user_email,
            price_id=settings.stripe_price_id_pro,
            success_url=f"{base_url}/dashboard?checkout=success",
            cancel_url=f"{base_url}/upgrade?checkout=canceled"
        )

        # Redirect to Stripe checkout
        return RedirectResponse(url=session_data["checkout_url"], status_code=303)

    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.

    This endpoint receives events from Stripe when:
    - Checkout sessions complete
    - Subscriptions are created/updated/deleted
    - Payments succeed/fail
    """
    try:
        # Get raw payload and signature
        payload = await request.body()
        signature = request.headers.get("stripe-signature")

        if not signature:
            raise HTTPException(status_code=400, detail="Missing signature")

        # Process webhook event
        result = stripe_service.handle_webhook_event(payload, signature)

        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/portal")
async def customer_portal(
    request: Request,
    user_id: str = Depends(require_auth())
):
    """
    Redirect to Stripe customer portal for subscription management.

    Users can:
    - Update payment method
    - View invoices
    - Cancel subscription
    """
    try:
        # Get base URL for return
        base_url = str(request.base_url).rstrip('/')

        # Create portal session
        portal_url = stripe_service.create_customer_portal_session(
            user_id=user_id,
            return_url=f"{base_url}/dashboard"
        )

        # Redirect to portal
        return RedirectResponse(url=portal_url, status_code=303)

    except Exception as e:
        logger.error(f"Error creating portal session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/success", response_class=HTMLResponse)
async def payment_success(request: Request, user_id: str = Depends(optional_auth())):
    """
    Payment success page (optional, can just redirect to dashboard).
    """
    return RedirectResponse(url="/dashboard?checkout=success", status_code=303)


@router.get("/cancel", response_class=HTMLResponse)
async def payment_canceled(request: Request, user_id: str = Depends(optional_auth())):
    """
    Payment canceled page (optional, can just redirect to upgrade).
    """
    return RedirectResponse(url="/upgrade?checkout=canceled", status_code=303)
