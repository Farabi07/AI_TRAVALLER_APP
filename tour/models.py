from django.db import models
from django.conf import settings

# Model to store curated trip / itinerary data
class Trip(models.Model):
	title = models.CharField(max_length=255, blank=True, null=True)
	image_url = models.URLField(max_length=2000, blank=True, null=True)
	location = models.CharField(max_length=255, blank=True, null=True)
	view_details = models.BooleanField(default=True, blank=True, null=True)
	share = models.BooleanField(default=True, blank=True, null=True)
	is_saved = models.BooleanField(default=True, blank=True, null=True)
	is_shared = models.BooleanField(default=False, blank=True, null=True)
	regenerate_plan = models.BooleanField(default=True, blank=True, null=True)
	
	# Duration broken out for easier querying
	duration_days = models.PositiveIntegerField(default=0, blank=True, null=True)
	duration_nights = models.PositiveIntegerField(default=0, blank=True, null=True)

	spots_count = models.PositiveIntegerField(default=0, blank=True, null=True)

	# Categories and structured itinerary stored as JSON for flexibility
	# `categories` is a list of strings (e.g. ["🏛️ History", "🍽️ Food"]).
	categories = models.JSONField(default=list, blank=True, null=True)

	description = models.TextField(blank=True, null=True)

	# `summary_itinerary` is a list of day objects, e.g.
	# [{"day": "Day 1", "title": "Historical Landmarks", "activities": ["...", ...]}, ...]
	summary_itinerary = models.JSONField(default=list, blank=True, null=True)

	# `details` stores the complete trip details including static_map, tour_spots, and daily schedules
	# Structure: {"static_map": {...}, "tour_spots_title": "...", "tour_spots": [...], "days": [...]}
	details = models.JSONField(default=dict, blank=True, null=True)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="+", null=True, blank=True)
	updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="+", null=True, blank=True)

	class Meta:
		ordering = ["-id"]

	def __str__(self) -> str:
		return self.title or f"Trip {self.id}"


class Post(models.Model):
	caption = models.TextField(blank=True, null=True)
	like = models.PositiveIntegerField(default=0, blank=True, null=True)
	
	title = models.CharField(max_length=255, blank=True, null=True)

	image_url = models.URLField(max_length=2000, blank=True, null=True)
	image = models.ImageField(upload_to="posts/", null=True, blank=True)
	location = models.CharField(max_length=2000, blank=True, null=True)
	latitude = models.FloatField(blank=True, null=True)
	longitude = models.FloatField(blank=True, null=True)
	view_details = models.BooleanField(default=True, blank=True, null=True)
	share = models.BooleanField(default=True, blank=True, null=True)
	is_saved = models.BooleanField(default=True, blank=True, null=True)  
	is_shared = models.BooleanField(default=False, blank=True, null=True)
	regenerate_plan = models.BooleanField(default=True, blank=True, null=True)
	# Duration broken out for easier querying
	duration_days = models.PositiveIntegerField(default=0, blank=True, null=True)
	duration_nights = models.PositiveIntegerField(default=0, blank=True, null=True)

	spots_count = models.PositiveIntegerField(default=0, blank=True, null=True)

	# Categories and structured itinerary stored as JSON for flexibility
	# `categories` is a list of strings (e.g. ["🏛️ History", "🍽️ Food"]).
	categories = models.JSONField(default=list, blank=True, null=True)

	description = models.TextField(blank=True, null=True)

	# `summary_itinerary` is a list of day objects, e.g.
	# [{"day": "Day 1", "title": "Historical Landmarks", "activities": ["...", ...]}, ...]
	summary_itinerary = models.JSONField(default=list, blank=True, null=True)

	# `details` stores the complete trip details including static_map, tour_spots, and daily schedules
	# Structure: {"static_map": {...}, "tour_spots_title": "...", "tour_spots": [...], "days": [...]}
	details = models.JSONField(default=dict, blank=True, null=True)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)
	updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.SET_NULL, related_name="+", null=True, blank=True)


	class Meta:
		ordering = ["-id"]

	def __str__(self):
		# Ensure __str__ always returns a string (title may be None)
		if self.title:
			return str(self.title)
		# fallback to id-based representation
		return f"Post {self.id}"


class PostComment(models.Model):
	post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_comments')
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
	text = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self) -> str:
		return (self.text[:50] + '...') if len(self.text) > 50 else self.text


class PostLike(models.Model):
	post = models.ForeignKey('tour.Post', related_name='likes', on_delete=models.CASCADE)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='post_likes', on_delete=models.CASCADE)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('post', 'user')
		ordering = ('-created_at',)

	def __str__(self):
		return f"{self.user_id} liked {self.post_id}"