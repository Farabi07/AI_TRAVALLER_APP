from django.contrib import admin
from .models import Trip


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
	list_display = ("title", "duration_days", "duration_nights", "spots_count", "created_at")
	list_filter = ("duration_days",)
	search_fields = ("title", "description")

from django.contrib import admin
from django.contrib.auth.models import Group

from .models import *

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
	list_display = [field.name for field in Post._meta.fields]
