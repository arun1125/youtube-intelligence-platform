"""
Stripe payment service for handling subscriptions.
"""

import stripe
import logging
from typing import Optional, Dict
from app.core.config import get_settings
from app.core.database import supabase_client

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure Stripe
stripe.api_key = settings.stripe_secret_key


class StripeService:
    """Service for managing Stripe subscriptions and payments."""

    def create_checkout_session(
        self,
        user_id: str,
        user_email: str,
        price_id: str,
        success_url: str,
        cancel_url: str
    ) -> Dict:
        """
        Create a Stripe checkout session for subscription.

        Args:
            user_id: Internal user ID
            user_email: User's email address
            price_id: Stripe price ID
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if user cancels

        Returns:
            Dict with session_id and checkout_url
        """
        try:
            # Check if customer already exists
            profile = supabase_client.table("profiles").select("stripe_customer_id").eq("id", user_id).single().execute()

            customer_id = profile.data.get("stripe_customer_id") if profile.data else None

            # Create or retrieve customer
            if not customer_id:
                customer = stripe.Customer.create(
                    email=user_email,
                    metadata={"user_id": user_id}
                )
                customer_id = customer.id

                # Save customer ID to database
                supabase_client.table("profiles").update({
                    "stripe_customer_id": customer_id
                }).eq("id", user_id).execute()

                logger.info(f"✓ Created Stripe customer {customer_id} for user {user_id}")

            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": user_id
                },
                subscription_data={
                    "metadata": {
                        "user_id": user_id
                    }
                }
            )

            logger.info(f"✓ Created checkout session {session.id} for user {user_id}")

            return {
                "session_id": session.id,
                "checkout_url": session.url
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            raise Exception(f"Payment error: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            raise

    def create_customer_portal_session(
        self,
        user_id: str,
        return_url: str
    ) -> str:
        """
        Create a Stripe customer portal session for managing subscription.

        Args:
            user_id: Internal user ID
            return_url: URL to return to after portal session

        Returns:
            Portal session URL
        """
        try:
            # Get customer ID from database
            profile = supabase_client.table("profiles").select("stripe_customer_id").eq("id", user_id).single().execute()

            customer_id = profile.data.get("stripe_customer_id") if profile.data else None

            if not customer_id:
                raise Exception("No Stripe customer found for user")

            # Create portal session
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url
            )

            logger.info(f"✓ Created portal session for customer {customer_id}")

            return session.url

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating portal session: {e}")
            raise Exception(f"Payment error: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating portal session: {e}")
            raise

    def handle_webhook_event(self, payload: bytes, signature: str) -> Dict:
        """
        Handle Stripe webhook events.

        Args:
            payload: Raw webhook payload
            signature: Stripe signature header

        Returns:
            Dict with processing status
        """
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, signature, settings.stripe_webhook_secret
            )

            logger.info(f"📨 Received Stripe webhook: {event['type']}")

            # Handle different event types
            if event["type"] == "checkout.session.completed":
                self._handle_checkout_completed(event["data"]["object"])

            elif event["type"] == "customer.subscription.created":
                self._handle_subscription_created(event["data"]["object"])

            elif event["type"] == "customer.subscription.updated":
                self._handle_subscription_updated(event["data"]["object"])

            elif event["type"] == "customer.subscription.deleted":
                self._handle_subscription_deleted(event["data"]["object"])

            elif event["type"] == "invoice.payment_succeeded":
                self._handle_payment_succeeded(event["data"]["object"])

            elif event["type"] == "invoice.payment_failed":
                self._handle_payment_failed(event["data"]["object"])

            return {"status": "success", "event": event["type"]}

        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise Exception("Invalid webhook signature")
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            raise

    def _handle_checkout_completed(self, session: Dict):
        """Handle successful checkout session."""
        user_id = session["metadata"].get("user_id")
        customer_id = session["customer"]
        subscription_id = session["subscription"]

        if not user_id:
            logger.warning("Checkout session missing user_id in metadata")
            return

        # Update user profile with subscription info
        supabase_client.table("profiles").update({
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "subscription_tier": "pro",
            "subscription_status": "active",
            "tests_limit": 999999  # Pro tier gets unlimited tests
        }).eq("id", user_id).execute()

        logger.info(f"✓ Activated Pro subscription for user {user_id}")

    def _handle_subscription_created(self, subscription: Dict):
        """Handle new subscription creation."""
        user_id = subscription["metadata"].get("user_id")

        if not user_id:
            logger.warning("Subscription missing user_id in metadata")
            return

        status = subscription["status"]
        is_active = status == "active"

        supabase_client.table("profiles").update({
            "stripe_subscription_id": subscription["id"],
            "subscription_tier": "pro" if is_active else "free",
            "subscription_status": status,
            "tests_limit": 999999 if is_active else 5  # Pro gets unlimited, free gets 5
        }).eq("id", user_id).execute()

        logger.info(f"✓ Created subscription {subscription['id']} for user {user_id}, status: {status}")

    def _handle_subscription_updated(self, subscription: Dict):
        """Handle subscription updates."""
        subscription_id = subscription["id"]
        status = subscription["status"]

        # Find user by subscription ID
        profile = supabase_client.table("profiles").select("id").eq(
            "stripe_subscription_id", subscription_id
        ).execute()

        if not profile.data:
            logger.warning(f"No user found for subscription {subscription_id}")
            return

        user_id = profile.data[0]["id"]

        # Determine subscription tier based on status
        is_pro = status in ["active", "trialing"]
        tier = "pro" if is_pro else "free"

        supabase_client.table("profiles").update({
            "subscription_tier": tier,
            "subscription_status": status,
            "tests_limit": 999999 if is_pro else 5  # Pro gets unlimited, free gets 5
        }).eq("id", user_id).execute()

        logger.info(f"✓ Updated subscription for user {user_id}: tier={tier}, status={status}")

    def _handle_subscription_deleted(self, subscription: Dict):
        """Handle subscription cancellation."""
        subscription_id = subscription["id"]

        # Find user by subscription ID
        profile = supabase_client.table("profiles").select("id").eq(
            "stripe_subscription_id", subscription_id
        ).execute()

        if not profile.data:
            logger.warning(f"No user found for subscription {subscription_id}")
            return

        user_id = profile.data[0]["id"]

        # Downgrade to free tier
        supabase_client.table("profiles").update({
            "subscription_tier": "free",
            "subscription_status": "canceled",
            "tests_limit": 5  # Reset to free tier limit
        }).eq("id", user_id).execute()

        logger.info(f"✓ Canceled subscription for user {user_id}, downgraded to free")

    def _handle_payment_succeeded(self, invoice: Dict):
        """Handle successful payment - reset billing cycle and log payment."""
        subscription_id = invoice.get("subscription")
        customer_id = invoice.get("customer")
        amount_paid = invoice.get("amount_paid", 0)
        currency = invoice.get("currency", "usd").upper()

        if not subscription_id:
            logger.info(f"✓ One-time payment received: {amount_paid/100:.2f} {currency}")
            return

        # Find user by subscription ID
        profile = supabase_client.table("profiles").select("id, tests_used_this_month").eq(
            "stripe_subscription_id", subscription_id
        ).execute()

        if not profile.data:
            logger.warning(f"No user found for subscription {subscription_id}")
            return

        user_id = profile.data[0]["id"]

        # Reset monthly usage on successful payment (new billing cycle)
        supabase_client.table("profiles").update({
            "subscription_status": "active",
            "tests_used_this_month": 0,
            "billing_cycle_start": "now()"
        }).eq("id", user_id).execute()

        logger.info(f"✓ Payment succeeded for user {user_id}: {amount_paid/100:.2f} {currency} - reset monthly usage")

    def _handle_payment_failed(self, invoice: Dict):
        """Handle failed payment - update status and log details for follow-up."""
        subscription_id = invoice.get("subscription")
        customer_id = invoice.get("customer")
        attempt_count = invoice.get("attempt_count", 1)
        next_attempt = invoice.get("next_payment_attempt")
        amount_due = invoice.get("amount_due", 0)
        currency = invoice.get("currency", "usd").upper()

        if not subscription_id:
            logger.warning(f"⚠️ Payment failed for non-subscription invoice")
            return

        # Find user by subscription ID
        profile = supabase_client.table("profiles").select("id, full_name").eq(
            "stripe_subscription_id", subscription_id
        ).execute()

        if not profile.data:
            logger.warning(f"No user found for subscription {subscription_id}")
            return

        user_id = profile.data[0]["id"]
        user_name = profile.data[0].get("full_name", "Unknown")

        # Update subscription status to past_due
        supabase_client.table("profiles").update({
            "subscription_status": "past_due"
        }).eq("id", user_id).execute()

        # Log detailed failure info for potential email follow-up
        logger.warning(
            f"⚠️ Payment failed for user {user_id} ({user_name}): "
            f"{amount_due/100:.2f} {currency}, attempt #{attempt_count}"
        )

        # Log usage event for analytics
        try:
            supabase_client.table("usage_logs").insert({
                "user_id": user_id,
                "action": "payment_failed",
                "metadata": {
                    "amount_due": amount_due,
                    "currency": currency,
                    "attempt_count": attempt_count,
                    "subscription_id": subscription_id
                }
            }).execute()
        except Exception as e:
            logger.error(f"Failed to log payment failure event: {e}")


# Singleton instance
stripe_service = StripeService()
