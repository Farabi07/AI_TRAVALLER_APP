
from django.urls import path
from tour.views import trip_plan_views as views


urlpatterns = [
	path('api/v1/trip/all/', views.getAllTrip),

	path('api/v1/trip/without_pagination/all/', views.getAllTripWithoutPagination),

	path('api/v1/trip/<int:pk>', views.getATrip),

	# path('api/v1/trip/search/', views.searchTrip),

	path('api/v1/trip/create/', views.createTrip),

	path('api/v1/trip/update/<int:pk>', views.updateTrip),

	path('api/v1/trip/delete/<int:pk>', views.deleteTrip),

]