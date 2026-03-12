from authentication.views import subscription_views as views
from django.urls import path

	

urlpatterns = [
    # ==========================================
    # Unlimited Card Generation Subscription ($4.99/month)
    # ==========================================
    path('api/v1/subscription/unlimited/checkout/', views.create_unlimited_checkout, name='create_unlimited_checkout'),
    path('api/v1/subscription/verify-session/', views.verify_checkout_session, name='verify_checkout_session'),
    path('api/v1/subscription/status/', views.get_subscription_status, name='get_subscription_status'),
    path('api/v1/subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    
    # ==========================================
    # VIP Support Subscription ($9.99/month)
    # ==========================================
    path('api/v1/subscription/vip-support/checkout/', views.create_vip_support_checkout, name='create_vip_support_checkout'),
    
    # TEST ONLY - Remove in production!
    path('api/v1/subscription/test-activate/', views.test_activate_subscription, name='test_activate_subscription'),
    
    # ==========================================
    # Existing Subscription Endpoints
    # ==========================================
    # API endpoint for creating a subscription
    path('api/v1/subscription/create/', views.create_subscription, name='create_subscription'),
    
    # Stripe webhook (also in main urls.py for backwards compatibility)
    path('api/v1/subscription/stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    
    # API endpoint for creating a Stripe customer
    path('api/v1/subscription/create-stripe-customer/', views.create_stripe_customer, name='create_stripe_customer'),
    
    # API endpoint for attaching a payment method to a Stripe customer
    path('api/v1/subscription/attach-payment-method/', views.attach_payment_method, name='attach_payment_method'),
    path('api/v1/create-payment-intent/', views.create_payment_intent, name='create_payment_intent'),
    # API endpoint for creating a payment method
    path('api/v1/subscription/create-payment-method/', views.create_payment_method, name='create_payment_method'),

    path('verify-inapp-purchase/', views.save_subscription, name='verify_inapp_purchase'),
    path('api/v1/subscription/activate/', views.subscription_status, name='subscription_status'),

    path('all-users-subscription-status/', views.all_users_subscription_status, name='all_users_subscription_status'),
]
