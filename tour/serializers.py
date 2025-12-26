from django.contrib.auth import get_user_model
from django.conf import settings

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from django_currentuser.middleware import (get_current_authenticated_user, get_current_user)

from djoser.serializers import UserCreateSerializer

from tour.models import *
from tour.models import PostLike  # explicit import to ensure it's available
from django.utils.translation import gettext_lazy as _
from authentication.models import User
from djoser import signals
from django.core.mail import send_mail
from django.template.loader import render_to_string



class TripListSerializer(serializers.ModelSerializer):
	created_by = serializers.SerializerMethodField()
	updated_by = serializers.SerializerMethodField()
	class Meta:
		model = Trip
		fields = '__all__'

	def get_created_by(self, obj):
		return obj.created_by.email if obj.created_by else obj.created_by
		
	def get_updated_by(self, obj):
		return obj.updated_by.email if obj.updated_by else obj.updated_by




class TripMinimalSerializer(serializers.ModelSerializer):
	class Meta:
		model = Trip
		fields = ['id', 'name']




class TripSerializer(serializers.ModelSerializer):
	class Meta:
		model = Trip
		fields = '__all__'
	
	def create(self, validated_data):
		modelObject = super().create(validated_data=validated_data)
		user = get_current_authenticated_user()
		if user is not None:
			modelObject.created_by = user
		modelObject.save()
		return modelObject
	
	def update(self, instance, validated_data):
		modelObject = super().update(instance=instance, validated_data=validated_data)
		user = get_current_authenticated_user()
		if user is not None:
			modelObject.updated_by = user
		modelObject.save()
		return modelObject


class PostCommentSerializer(serializers.ModelSerializer):
	# include nested user info for each comment
	user = serializers.SerializerMethodField()

	class Meta:
		model = PostComment
		fields = ('id', 'user', 'text', 'created_at')

	def get_user(self, obj):
		if obj.user:
			# helper to safely decode bytes to string
			def _to_str(val):
				if isinstance(val, (bytes, bytearray)):
					try:
						return val.decode('utf-8')
					except Exception:
						return str(val)
				return val

			image_url = None
			try:
				user_image = getattr(obj.user, 'image', None)
				if user_image:
					file_url = user_image.url
					request = self.context.get('request') if hasattr(self, 'context') else None
					if request is not None:
						file_url = request.build_absolute_uri(file_url)
					image_url = file_url
			except Exception:
				# ignore image errors and fall back to None
				image_url = None

			return {
				'id': obj.user.id,
				'username': _to_str(getattr(obj.user, 'username', None)),
				'full_name': _to_str(getattr(obj.user, 'full_name', None)),
				'image': image_url,
			}
		return None
	

class PostListSerializer(serializers.ModelSerializer):
	# reuse a nested user representation for list responses
	class UserNestedSerializer(serializers.ModelSerializer):
		class Meta:
			model = User
			fields = ('id', 'username', 'email', 'full_name', 'first_name', 'last_name','image')

	created_by = UserNestedSerializer(read_only=True)
	updated_by = UserNestedSerializer(read_only=True)
	# expose like count, whether current user liked it, and comments in list responses
	like_count = serializers.SerializerMethodField()
	liked_by_user = serializers.SerializerMethodField()
	map_url = serializers.SerializerMethodField()
	# will be populated with PostCommentSerializer below; import happens later in file
	post_comments = serializers.SerializerMethodField()

	class Meta:
		model = Post
		fields = '__all__'

	def get_like_count(self, obj):
		# If queryset was annotated with like_count, use it; otherwise count from PostLike relation
		try:
			if hasattr(obj, 'like_count'):
				return obj.like_count
			return obj.likes.count()
		except Exception:
			return 0

	def get_liked_by_user(self, obj):
			# returns True if the request.user has liked this post
		request = self.context.get('request') if hasattr(self, 'context') else None
		if request is None or request.user is None or request.user.is_anonymous:
			return False
		try:
			# use annotated relation when possible to avoid extra queries
			return obj.likes.filter(user=request.user).exists()
		except Exception:
			return False

	def get_map_url(self, obj):
		# Generate Google Maps web link if lat/lng available
		if obj.latitude and obj.longitude:
			return f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
		elif obj.location:
			# Fallback: use location name if lat/lng not available
			return f"https://www.google.com/maps/search/?api=1&query={obj.location}"
		return None

	def get_post_comments(self, obj):
		try:
			comments = obj.post_comments.all()[:5]  # return recent 5 comments in list view
			# pass parent context so comment serializer can build absolute urls
			return PostCommentSerializer(comments, many=True, context=self.context).data
		except Exception:
			# If DB table doesn't exist yet (migrations not applied) or other DB errors,
			# return empty list so the list endpoint doesn't 500. Remove this guard after migrations.
			return []





class PostMinimalListSerializer(serializers.ModelSerializer):
	class Meta:
		model = Post
		fields = ['id', 'name']


class PostSerializer(serializers.ModelSerializer):
	# Nested user representation for created_by/updated_by
	class UserNestedSerializer(serializers.ModelSerializer):
		class Meta:
			model = User
			fields = ('id', 'username', 'email', 'full_name', 'first_name', 'last_name','image')

	created_by = UserNestedSerializer(read_only=True)
	updated_by = UserNestedSerializer(read_only=True)
	liked_by_user = serializers.SerializerMethodField()
	map_url = serializers.SerializerMethodField()
	class Meta:
		model = Post
		fields = '__all__'
	
	def create(self, validated_data):
		modelObject = super().create(validated_data=validated_data)
		user = get_current_authenticated_user()
		if user is not None:
			modelObject.created_by = user

		# If an image file was uploaded, set image_url to the file's URL
		if hasattr(modelObject, 'image') and modelObject.image:
			request = self.context.get('request') if hasattr(self, 'context') else None
			file_url = modelObject.image.url
			if request is not None:
				file_url = request.build_absolute_uri(file_url)
			modelObject.image_url = file_url

		modelObject.save()
		return modelObject
	
	def update(self, instance, validated_data):
		modelObject = super().update(instance=instance, validated_data=validated_data)
		user = get_current_authenticated_user()
		if user is not None:
			modelObject.updated_by = user

		# If image was updated/added, ensure image_url is updated too
		if hasattr(modelObject, 'image') and modelObject.image:
			request = self.context.get('request') if hasattr(self, 'context') else None
			file_url = modelObject.image.url
			if request is not None:
				file_url = request.build_absolute_uri(file_url)
			modelObject.image_url = file_url

		modelObject.save()
		return modelObject

	# include all comments in detail serializer
	post_comments = serializers.SerializerMethodField()

	def get_post_comments(self, obj):
		try:
			comments = obj.post_comments.all()
			return PostCommentSerializer(comments, many=True, context=self.context).data
		except Exception:
			return []

	def get_map_url(self, obj):
		# Generate Google Maps web link if lat/lng available
		if obj.latitude and obj.longitude:
			return f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
		elif obj.location:
			# Fallback: use location name if lat/lng not available
			return f"https://www.google.com/maps/search/?api=1&query={obj.location}"
		return None

	def get_liked_by_user(self, obj):
		request = self.context.get('request') if hasattr(self, 'context') else None
		if request is None or request.user is None or request.user.is_anonymous:
			return False
		try:
			return obj.likes.filter(user=request.user).exists()
		except Exception:
			return False
# tour/serializers.py
class PostLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostLike
        fields = ('id', 'post', 'user', 'created_at')
        read_only_fields = ('user', 'created_at')