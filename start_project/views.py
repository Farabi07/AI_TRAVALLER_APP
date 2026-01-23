from django.http import HttpResponse

def index(request):
	return HttpResponse("Welcome to Our AI Travel App.")

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
# from allauth.socialaccount.exceptions import OAuth2Error
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings



from dj_rest_auth.registration.views import SocialLoginView

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomGoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = settings.GOOGLE_CALLBACK_URL
    client_class = OAuth2Client

    def get_response(self):
        response = super().get_response()
        user = self.user

        # generate JWT tokens manually
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # build user response
        user_data = {
            "refresh": str(refresh),
            "access": str(access),
            "id": user.id,
            "city": user.city if hasattr(user, 'city') else None,
            "country": user.country if hasattr(user, 'country') else None,
            "created_by": user.created_by.email if getattr(user, 'created_by', None) else None,
            "updated_by": user.updated_by.email if getattr(user, 'updated_by', None) else None,
            "last_login": user.last_login,
            "full_name": getattr(user, 'full_name', ""),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "email": user.email,
            "gender": getattr(user, 'gender', None),
            "primary_phone": getattr(user, 'primary_phone', None),
            "secondary_phone": getattr(user, 'secondary_phone', None),
            "user_type": getattr(user, 'user_type', None),
            "date_of_birth": getattr(user, 'date_of_birth', None),
            "is_active": user.is_active,
            "is_admin": user.is_superuser,
            "role": getattr(user, 'role', None),
            "street_address_one": getattr(user, 'street_address_one', None),
            "street_address_two": getattr(user, 'street_address_two', None),
            "postal_code": getattr(user, 'postal_code', None),
            "image": user.image.url if hasattr(user, 'image') and user.image else None,
            "nid": getattr(user, 'nid', None),
            "created_at": user.created_at if hasattr(user, 'created_at') else None,
            "updated_at": user.updated_at if hasattr(user, 'updated_at') else None,
        }

        return Response(user_data)



from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
import json
import jwt

User = get_user_model()

from django.shortcuts import render

def my_html_view(request):
    context = {
        "title": "Welcome!",
        "message": "This is a rendered HTML page.",
    }
    return render(request, "privacy.html", context)