import stripe
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta, datetime
from django.views.decorators.csrf import csrf_exempt
from authentication.models import Subscription, SubscriptionPlan
from django.conf import settings
import json
import logging
from django.http import JsonResponse
from django.contrib.auth import get_user_model

# Use Stripe secret key from settings
stripe.api_key = settings.STRIPE_SECRET_KEY

# Logging setup
logger = logging.getLogger(__name__)

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def create_subscription(request):
#     plan_id = request.data.get('plan_id')  # Stripe Price ID
#     user = request.user

#     # Get or create the subscription for the user
#     subscription, created = Subscription.objects.get_or_create(user=user)

#     # Get the plan from your DB
#     plan = SubscriptionPlan.objects.filter(plan_id=plan_id).first()
#     if not plan:
#         return Response({"error": "Invalid plan."}, status=400)

#     try:
#         # Create a Stripe Checkout Session for subscription
#         checkout_session = stripe.checkout.Session.create(
#             payment_method_types=['card'],
#             mode='subscription',
#             line_items=[{
#                 'price': plan.plan_id,  # Stripe Price ID
#                 'quantity': 1,
#             }],
#             customer_email=user.email,
#             success_url='https://your-frontend.com/success?session_id={CHECKOUT_SESSION_ID}',
#             cancel_url='https://your-frontend.com/cancel',
#         )
#         # Optionally, store the plan on the user's subscription for later use
#         subscription.plan = plan
#         subscription.save(update_fields=["plan"])
#         return Response({"checkout_url": checkout_session.url})
#     except Exception as e:
#         return Response({"error": str(e)}, status=400)
stripe.api_key = settings.STRIPE_SECRET_KEY
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt



@csrf_exempt
def create_payment_intent(request):
    try:
        data = json.loads(request.body)
        print("Received data:", data)
        plan_id = data.get('plan_id')
        user = request.user

        # Look up the plan
        plan = SubscriptionPlan.objects.filter(plan_id=plan_id).first()
        if not plan:
            return JsonResponse({'error': 'Invalid plan.'}, status=400)

        # Create PaymentIntent with plan price and metadata
        payment_intent = stripe.PaymentIntent.create(
            amount=int(plan.price * 100),  # Stripe expects cents
            currency='usd',
            metadata={
                'user_id': str(user.id),
                'plan_id': plan_id
            }
        )

        return JsonResponse({
            'client_secret': payment_intent.client_secret
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_stripe_customer(request):
    user = request.user
    try:
        # Create a new Stripe customer using the user's email
        customer = stripe.Customer.create(email=user.email)

        # Respond with the customer ID (useful for later attachment of payment methods or subscription creation)
        return Response({"customer_id": customer.id}, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def attach_payment_method(request):
    user = request.user
    payment_method_id = request.data.get('payment_method_id')  # Get the payment method ID from the request
    customer_id = request.data.get('customer_id')  # Get the customer ID from the request

    try:
        # Attach the payment method to the customer
        stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)

        # Set the attached payment method as the default for the customer
        stripe.Customer.modify(
            customer_id,
            invoice_settings={'default_payment_method': payment_method_id},
        )

        return Response({"message": "Payment method attached successfully."}, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_method(request):
    card_data = request.data.get('card_data')  # Card data is passed as a parameter (e.g., number, exp_month, exp_year, cvc)
    try:
        # Create a payment method using Stripe's API
        payment_method = stripe.PaymentMethod.create(
            type="card",
            card=card_data
        )
        return Response({"payment_method_id": payment_method.id}, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_subscription(request):
    user = request.user
    plan_id = request.data.get('plan_id')  # Stripe Price ID of the plan
    customer_id = request.data.get('customer_id')  # The customer ID returned earlier
    payment_method_id = request.data.get('payment_method_id')  # The payment method ID attached to the customer

    try:
        # Create the subscription using the provided details
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": plan_id}],  # Stripe Price ID (Plan ID)
            default_payment_method=payment_method_id  # Use the attached payment method
        )

        return Response({"subscription_id": subscription.id}, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_activate_subscription(request):
    """
    TEST ONLY: Manually activate subscription for testing when webhooks don't work.
    This simulates what the webhook does after successful payment.
    Remove this endpoint in production!
    
    Optional parameter: subscription_type ('unlimited_cards' or 'vip_support')
    """
    user = request.user
    subscription_type = request.data.get('subscription_type', 'unlimited_cards')
    
    # Map subscription type to product_id
    product_id_map = {
        'unlimited_cards': 'unlimited_cards_monthly',
        'vip_support': 'vip_support_monthly'
    }
    product_id = product_id_map.get(subscription_type, 'unlimited_cards_monthly')
    
    try:
        subscription, _ = Subscription.objects.get_or_create(user=user)
        
        # Simulate successful Stripe subscription
        subscription.is_active = True
        subscription.started_at = timezone.now()
        subscription.expires_at = timezone.now() + timedelta(days=30)
        subscription.status_is = 'active'
        subscription.product_id = product_id
        subscription.stripe_subscription_id = f'test_sub_{subscription_type}_{user.id}'
        subscription.save()
        
        # Update user.is_subscribed field
        user.is_subscribed = True
        user.save(update_fields=['is_subscribed'])
        
        logger.info(f"TEST: Manually activated {subscription_type} subscription for user {user.id}")
        
        return Response({
            'success': True,
            'message': f'{subscription_type} subscription activated for testing',
            'subscription': {
                'is_active': subscription.is_active,
                'expires_at': subscription.expires_at,
                'status': subscription.status_is,
                'product_id': subscription.product_id,
            }
        }, status=200)
        
    except Exception as e:
        logger.error(f"Test activation error: {str(e)}")
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_checkout_session(request):
    """
    PROPER WAY: Verify Stripe checkout session and activate subscription.
    
    After payment, frontend calls this with the session_id from Stripe.
    This endpoint retrieves the session from Stripe, verifies payment,
    and activates the subscription.
    
    Call this after successful checkout redirect.
    """
    user = request.user
    session_id = request.data.get('session_id')
    
    if not session_id:
        return Response({'error': 'session_id is required'}, status=400)
    
    try:
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        logger.info(f"Verifying session {session_id} for user {user.id}")
        logger.info(f"Session status: {session.payment_status}, mode: {session.mode}")
        
        # Verify the session belongs to this user
        if session.metadata.get('user_id') != str(user.id):
            return Response({'error': 'Session does not belong to this user'}, status=403)
        
        # Check if payment was successful
        if session.payment_status != 'paid':
            return Response({
                'error': 'Payment not completed',
                'payment_status': session.payment_status
            }, status=400)
        
        # Check if it's a subscription
        if session.mode != 'subscription':
            return Response({'error': 'Not a subscription session'}, status=400)
        
        # Get subscription type from metadata
        subscription_type = session.metadata.get('subscription_type', 'unlimited_cards')
        
        # Map subscription type to product_id
        product_id_map = {
            'unlimited_cards': 'unlimited_cards_monthly',
            'vip_support': 'vip_support_monthly'
        }
        product_id = product_id_map.get(subscription_type, 'unlimited_cards_monthly')
        
        # Activate the subscription
        subscription, _ = Subscription.objects.get_or_create(user=user)
        subscription.stripe_customer_id = session.customer
        subscription.stripe_subscription_id = session.subscription
        subscription.is_active = True
        subscription.started_at = timezone.now()
        subscription.expires_at = timezone.now() + timedelta(days=30)
        subscription.status_is = 'active'
        subscription.product_id = product_id
        subscription.save()
        
        # Update user.is_subscribed field
        user.is_subscribed = True
        user.save(update_fields=['is_subscribed'])
        
        logger.info(f"✅ Subscription activated for user {user.id} via session verification with product: {product_id}")
        
        return Response({
            'success': True,
            'message': 'Subscription activated successfully',
            'subscription': {
                'is_active': subscription.is_active,
                'expires_at': subscription.expires_at,
                'status': subscription.status_is,
                'stripe_subscription_id': subscription.stripe_subscription_id,
                'product_id': subscription.product_id,
            }
        }, status=200)
        
    except stripe.error.InvalidRequestError as e:
        logger.error(f"Invalid session ID: {str(e)}")
        return Response({'error': 'Invalid session ID'}, status=400)
    except Exception as e:
        logger.error(f"Session verification error: {str(e)}")
        return Response({'error': str(e)}, status=400)


@csrf_exempt
def stripe_webhook(request):
    """
    Enhanced Stripe webhook handler for both payment intents and subscriptions.
    """
    from django.utils import timezone
    from datetime import timedelta

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET
    
    logger.info("="*50)
    logger.info("Stripe webhook called!")
    logger.info(f"Signature header present: {bool(sig_header)}")
    logger.info(f"Endpoint secret configured: {bool(endpoint_secret)}")
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        logger.info(f"✅ Stripe webhook event received: {event['type']}")
        logger.info(f"Event data: {json.dumps(event['data'], indent=2)}")

        # Handle subscription events (for $4.99/month unlimited plan)
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            if session.get('mode') == 'subscription':
                user_id = session['metadata'].get('user_id')
                subscription_id = session.get('subscription')
                customer_id = session.get('customer')
                subscription_type = session['metadata'].get('subscription_type', 'unlimited_cards')
                
                # Map subscription type to product_id
                product_id_map = {
                    'unlimited_cards': 'unlimited_cards_monthly',
                    'vip_support': 'vip_support_monthly'
                }
                product_id = product_id_map.get(subscription_type, 'unlimited_cards_monthly')
                
                logger.info(f"Subscription checkout completed - user_id: {user_id}, subscription_id: {subscription_id}, type: {subscription_type}")
                
                User = get_user_model()
                user = User.objects.filter(id=user_id).first()
                
                if user:
                    subscription, _ = Subscription.objects.get_or_create(user=user)
                    subscription.stripe_customer_id = customer_id
                    subscription.stripe_subscription_id = subscription_id
                    subscription.is_active = True
                    subscription.started_at = timezone.now()
                    subscription.expires_at = timezone.now() + timedelta(days=30)  # Monthly subscription
                    subscription.status_is = 'active'
                    subscription.product_id = product_id
                    subscription.save()
                    
                    # Update user.is_subscribed field
                    user.is_subscribed = True
                    user.save(update_fields=['is_subscribed'])
                    
                    logger.info(f"Subscription activated for user {user_id} with product: {product_id}")
                else:
                    logger.error(f"User not found: {user_id}")

        elif event['type'] == 'customer.subscription.updated':
            subscription_obj = event['data']['object']
            stripe_subscription_id = subscription_obj['id']
            
            try:
                subscription = Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
                
                # Update subscription status
                if subscription_obj['status'] == 'active':
                    subscription.is_active = True
                    subscription.status_is = 'active'
                    # Update expiry date based on current period end
                    subscription.expires_at = timezone.datetime.fromtimestamp(
                        subscription_obj['current_period_end'], 
                        tz=timezone.get_current_timezone()
                    )
                    
                    # Update user.is_subscribed field
                    subscription.user.is_subscribed = True
                    subscription.user.save(update_fields=['is_subscribed'])
                    
                elif subscription_obj['status'] in ['canceled', 'unpaid', 'past_due']:
                    subscription.is_active = False
                    subscription.status_is = subscription_obj['status']
                    
                    # Update user.is_subscribed field
                    subscription.user.is_subscribed = False
                    subscription.user.save(update_fields=['is_subscribed'])
                
                subscription.save()
                logger.info(f"Subscription {stripe_subscription_id} updated to status: {subscription_obj['status']}")
                
            except Subscription.DoesNotExist:
                logger.warning(f"Subscription not found for Stripe ID: {stripe_subscription_id}")

        elif event['type'] == 'customer.subscription.deleted':
            subscription_obj = event['data']['object']
            stripe_subscription_id = subscription_obj['id']
            
            try:
                subscription = Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
                subscription.is_active = False
                subscription.status_is = 'canceled'
                subscription.save()
                
                # Update user.is_subscribed field
                subscription.user.is_subscribed = False
                subscription.user.save(update_fields=['is_subscribed'])
                
                logger.info(f"Subscription {stripe_subscription_id} canceled")
                
            except Subscription.DoesNotExist:
                logger.warning(f"Subscription not found for Stripe ID: {stripe_subscription_id}")

        # Handle one-time payment intents (existing functionality)
        elif event['type'] == 'payment_intent.succeeded':
            intent = event['data']['object']
            user_id = intent['metadata'].get('user_id')
            plan_id = intent['metadata'].get('plan_id')
            payment_intent_id = intent['id']
            amount = intent.get('amount_received', 0) / 100.0

            logger.info(f"PaymentIntent succeeded - user_id: {user_id}, plan_id: {plan_id}, amount: ${amount}")

            from authentication.models import SubscriptionPlan
            User = get_user_model()
            user = User.objects.filter(id=user_id).first()
            plan = SubscriptionPlan.objects.filter(plan_id=plan_id).first()
            
            if user and plan:
                subscription, _ = Subscription.objects.get_or_create(user=user)
                subscription.is_active = True
                subscription.started_at = timezone.now()
                subscription.expires_at = timezone.now() + timedelta(days=plan.duration_days)
                subscription.payment_method_token = payment_intent_id
                subscription.status_is = 'active'
                subscription.save()
                
                # Update user.is_subscribed field
                user.is_subscribed = True
                user.save(update_fields=['is_subscribed'])
                
                logger.info(f"One-time subscription activated for user {user_id}")
            else:
                logger.error(f"User or plan not found - user_id: {user_id}, plan_id: {plan_id}")
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)
    
from datetime import datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from authentication.models import Subscription
import logging

# ============================================
# NEW: Stripe Subscription for Unlimited Card Generation
# ============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_unlimited_checkout(request):
    """
    Create a Stripe checkout session for $4.99/month unlimited card generation subscription.
    """
    user = request.user
    
    try:
        # Get or create subscription record
        subscription, _ = Subscription.objects.get_or_create(user=user)
        
        # Check if user already has an active subscription
        if subscription.is_subscription_active():
            # Map product_id to readable name
            product_names = {
                'unlimited_cards_monthly': 'Unlimited Card Generation ($4.99/month)',
                'vip_support_monthly': 'VIP Support ($9.99/month)'
            }
            current_plan = product_names.get(subscription.product_id, subscription.product_id)
            
            return Response({
                'error': 'You already have an active subscription',
                'message': f'You are currently subscribed to {current_plan}. Please cancel your existing subscription before subscribing to a new plan.',
                'subscription': {
                    'product_id': subscription.product_id,
                    'product_name': current_plan,
                    'expires_at': subscription.expires_at,
                    'status': subscription.status_is,
                    'started_at': subscription.started_at
                }
            }, status=400)
        
        # Create or get Stripe customer
        if not subscription.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip() or user.email,
                metadata={'user_id': str(user.id)}
            )
            subscription.stripe_customer_id = customer.id
            subscription.save(update_fields=['stripe_customer_id'])
        else:
            customer_id = subscription.stripe_customer_id
        
        # Create Stripe Checkout Session
        # Note: You need to create this price in your Stripe Dashboard first
        # or update with your actual Stripe Price ID
        checkout_session = stripe.checkout.Session.create(
            customer=subscription.stripe_customer_id,
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': 499,  # $4.99 in cents
                    'recurring': {
                        'interval': 'month',
                    },
                    'product_data': {
                        'name': 'Unlimited Card Generation',
                        'description': 'Generate unlimited travel itinerary cards',
                    },
                },
                'quantity': 1,
            }],
            success_url=request.data.get('success_url', 'https://your-frontend.com/success?session_id={CHECKOUT_SESSION_ID}'),
            cancel_url=request.data.get('cancel_url', 'https://your-frontend.com/cancel'),
            metadata={
                'user_id': str(user.id),
                'subscription_type': 'unlimited_cards'
            }
        )
        
        return Response({
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id
        }, status=200)
        
    except Exception as e:
        logger.error(f"Stripe checkout error for user {user.id}: {str(e)}")
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_vip_support_checkout(request):
    """
    Create a Stripe checkout session for $9.99/month VIP Support subscription.
    """
    user = request.user
    
    try:
        # Get or create subscription record
        subscription, _ = Subscription.objects.get_or_create(user=user)
        
        # Check if user already has an active subscription
        if subscription.is_subscription_active():
            # Map product_id to readable name
            product_names = {
                'unlimited_cards_monthly': 'Unlimited Card Generation ($4.99/month)',
                'vip_support_monthly': 'VIP Support ($9.99/month)'
            }
            current_plan = product_names.get(subscription.product_id, subscription.product_id)
            
            return Response({
                'error': 'You already have an active subscription',
                'message': f'You are currently subscribed to {current_plan}. Please cancel your existing subscription before subscribing to a new plan.',
                'subscription': {
                    'product_id': subscription.product_id,
                    'product_name': current_plan,
                    'expires_at': subscription.expires_at,
                    'status': subscription.status_is,
                    'started_at': subscription.started_at
                }
            }, status=400)
        
        # Create or get Stripe customer
        if not subscription.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip() or user.email,
                metadata={'user_id': str(user.id)}
            )
            subscription.stripe_customer_id = customer.id
            subscription.save(update_fields=['stripe_customer_id'])
        else:
            customer_id = subscription.stripe_customer_id
        
        # Create Stripe Checkout Session for VIP Support
        checkout_session = stripe.checkout.Session.create(
            customer=subscription.stripe_customer_id,
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': 999,  # $9.99 in cents
                    'recurring': {
                        'interval': 'month',
                    },
                    'product_data': {
                        'name': 'VIP Support',
                        'description': 'Priority customer support and premium features',
                    },
                },
                'quantity': 1,
            }],
            success_url=request.data.get('success_url', 'https://your-frontend.com/success?session_id={CHECKOUT_SESSION_ID}'),
            cancel_url=request.data.get('cancel_url', 'https://your-frontend.com/cancel'),
            metadata={
                'user_id': str(user.id),
                'subscription_type': 'vip_support'
            }
        )
        
        return Response({
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id
        }, status=200)
        
    except Exception as e:
        logger.error(f"Stripe VIP checkout error for user {user.id}: {str(e)}")
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subscription_status(request):
    """
    Get current user's subscription and trial status.
    """
    user = request.user
    
    try:
        subscription = Subscription.objects.get(user=user)
        subscription.sync_status()
        has_active_subscription = subscription.is_subscription_active()
        
        # Check if there's a pending checkout (has customer_id but no subscription_id)
        has_pending_checkout = (
            subscription.stripe_customer_id and 
            not subscription.stripe_subscription_id and
            not subscription.is_active
        )
        
        # Debug logging
        logger.info(f"User {user.id} subscription check:")
        logger.info(f"  - is_active: {subscription.is_active}")
        logger.info(f"  - expires_at: {subscription.expires_at}")
        logger.info(f"  - stripe_subscription_id: {subscription.stripe_subscription_id}")
        logger.info(f"  - is_subscription_active(): {subscription.is_subscription_active()}")
        logger.info(f"  - has_pending_checkout: {has_pending_checkout}")
        
        return Response({
            'has_active_subscription': has_active_subscription,
            'has_pending_checkout': has_pending_checkout,
            'trial_days_left': user.get_trial_days_left(),
            'cards_generated_today': user.get_cards_generated_today(),
            'can_generate_card': user.can_generate_card()[0],
            'subscription_status': subscription.status_is,
            'expires_at': subscription.expires_at if has_active_subscription else None,
            'stripe_customer_id': subscription.stripe_customer_id,
            'stripe_subscription_id': subscription.stripe_subscription_id,
            'user_is_subscribed': user.is_subscribed,
            # Debug info
            'debug': {
                'is_active': subscription.is_active,
                'started_at': subscription.started_at,
                'product_id': subscription.product_id,
            }
        }, status=200)
        
    except Subscription.DoesNotExist:
        # Create subscription if doesn't exist
        subscription = Subscription.objects.create(user=user)
        subscription.start_trial()
        
        return Response({
            'has_active_subscription': False,
            'trial_days_left': user.get_trial_days_left(),
            'cards_generated_today': user.get_cards_generated_today(),
            'can_generate_card': user.can_generate_card()[0],
            'subscription_status': subscription.status_is,
            'expires_at': None,
        }, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """
    Cancel user's Stripe subscription.
    """
    user = request.user
    
    try:
        subscription = Subscription.objects.get(user=user)
        
        if not subscription.stripe_subscription_id:
            return Response({'error': 'No active Stripe subscription found'}, status=400)
        
        # Cancel the subscription in Stripe
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        return Response({
            'message': 'Subscription will be cancelled at the end of billing period',
            'expires_at': subscription.expires_at
        }, status=200)
        
    except Subscription.DoesNotExist:
        return Response({'error': 'No subscription found'}, status=404)
    except Exception as e:
        logger.error(f"Cancel subscription error for user {user.id}: {str(e)}")
        return Response({'error': str(e)}, status=400)


# ============================================
# Original code continues below
# ============================================

# Map product_id to subscription duration in days
PRODUCT_DURATION_MAP = {
    'family_mode_monthly': 30,
    'family_mode_yearly': 365,
    'boss_mode_monthly': 30,
    'boss_mode_yearly': 365,
}

# Logging setup for debugging
logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_subscription(request):
    data = request.data
    user = request.user

    logger.info(f"Received data: {data}")

    product_id = data.get('product_id')
    duration_days = PRODUCT_DURATION_MAP.get(product_id)
    if not duration_days:
        return Response({'error': 'Invalid product_id.'}, status=400)

    # Get price from frontend (optional)
    price = data.get('price')  # <-- Accept price from frontend

    started_at = timezone.now()
    expires_at = started_at + timezone.timedelta(days=duration_days)

    subscription, _ = Subscription.objects.get_or_create(user=user)
    subscription.is_active = True
    subscription.started_at = started_at
    subscription.expires_at = expires_at
    subscription.product_id = product_id
    subscription.platform = data.get('platform')
    subscription.purchase_token = data.get('purchase_token')
    subscription.transaction_id = data.get('transaction_id')
    subscription.original_transaction_id = data.get('original_transaction_id')
    if price is not None:
        subscription.price = price  # <-- Save price if your model has this field

    purchase_date_str = data.get('purchase_date')
    if purchase_date_str:
        try:
            normalized_purchase_date = purchase_date_str.replace('Z', '+00:00')
            subscription.purchase_date = datetime.fromisoformat(normalized_purchase_date)
        except ValueError as e:
            logger.error(f"Error parsing purchase_date: {purchase_date_str}. Error: {e}")
            return Response({'error': 'Invalid purchase_date format.'}, status=400)

    subscription.status_is = 'active subscription'
    subscription.save()
    
    # Update user.is_subscribed field
    user.is_subscribed = True
    user.save(update_fields=['is_subscribed'])

    return Response({'success': True, 'message': 'Subscription activated.'})
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_status(request):
    user = request.user
    try:
        subscription = Subscription.objects.get(user=user)
        
        # Sync status to ensure it's up to date
        subscription.sync_status()
        
        return Response({
            "status": subscription.status_is,
            "expires_at": subscription.expires_at,
        })
        
    except Subscription.DoesNotExist:
        # This should rarely happen if signal is working properly
        # But as a fallback, create subscription and start trial
        subscription = Subscription.objects.create(user=user)
        subscription.start_trial()
        
        return Response({
            "status": subscription.status_is,
            "expires_at": subscription.expires_at,
        })
    
@api_view(['GET'])
def all_users_subscription_status(request):
    User = get_user_model()
    all_users = User.objects.all()
    users_list = []
    subscriber_count = 0
    non_subscriber_count = 0

    for user in all_users:
        try:
            subscription = Subscription.objects.get(user=user)
            if subscription.is_subscription_active():
                status = "subscriber"
                subscriber_count += 1
            else:
                status = "non-subscriber"
                non_subscriber_count += 1
        except Subscription.DoesNotExist:
            status = "non-subscriber"
            non_subscriber_count += 1

        # Get the absolute image URL if image exists
        if user.image:
            image_url = request.build_absolute_uri(user.image.url)
        else:
            image_url = None

        users_list.append({
            "id": user.id,
            "email": user.email,
            "full_name": getattr(user, "full_name", ""),
            "status": status,
            "image": image_url,
        })

    result = {
        "users": users_list,
        "subscriber_count": subscriber_count,
        "non_subscriber_count": non_subscriber_count,
        "total_users": all_users.count()
    }
    return Response(result)