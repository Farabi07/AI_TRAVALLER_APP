from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from tour.models import Trip, Post
from tour.serializers import TripSerializer, TripListSerializer
# from authentication.filters import TripFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from drf_spectacular.utils import  extend_schema, OpenApiParameter
from commons.pagination import Pagination
from django.db import transaction




# Create your views here.

@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=TripSerializer,
	responses=TripSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllTrip(request):
	# Only return trips created by the current user
	trips = Trip.objects.filter(created_by=request.user)
	total_elements = trips.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	trips = pagination.paginate_data(trips)

	serializer = TripListSerializer(trips, many=True)

	response = {
		'trips': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	return Response(response, status=status.HTTP_200_OK)




@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=TripSerializer,
	responses=TripSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllTripWithoutPagination(request):
	# Only return trips created by the current user
	trips = Trip.objects.filter(created_by=request.user)
	serializer = TripListSerializer(trips, many=True)
	return Response({'trips': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=TripSerializer, responses=TripSerializer)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getATrip(request, pk):
	try:
		role = Trip.objects.get(pk=pk)
		serializer = TripSerializer(role)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Trip id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




# @extend_schema(request=TripSerializer, responses=TripSerializer)
# @api_view(['GET'])
# # @permission_classes([IsAuthenticated])
# # @has_permissions([PermissionEnum.PRODUCT_DETAILS.name])
# def searchTrip(request):

# 	trips = TripFilter(request.GET, queryset=Trip.objects.all())
# 	trips = trips.qs

# 	print('trips: ', trips)

# 	total_elements = trips.count()

# 	page = request.query_params.get('page')
# 	size = request.query_params.get('size')

# 	# Pagination
# 	pagination = Pagination()
# 	pagination.page = page
# 	pagination.size = size
# 	trips = pagination.paginate_data(trips)

# 	serializer = TripListSerializer(trips, many=True)

# 	response = {
# 		'trips': serializer.data,
# 		'page': pagination.page,
# 		'size': pagination.size,
# 		'total_pages': pagination.total_pages,
# 		'total_elements': total_elements,
# 	}

# 	if len(trips) > 0:
# 		return Response(response, status=status.HTTP_200_OK)
# 	else:
# 		return Response({'detail': f"There are no trips matching your search"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=TripSerializer, responses=TripSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createTrip(request):
	data = request.data
	
	# Handle nested structure: extract trip and details objects
	if 'trip' in data and 'details' in data:
		trip_data = data.get('trip', {})
		details_data = data.get('details', {})
		
		# Flatten trip data
		flattened_data = {}
		for key, value in trip_data.items():
			if key == 'duration' and isinstance(value, dict):
				# Extract duration.days and duration.nights
				flattened_data['duration_days'] = value.get('days', 0)
				flattened_data['duration_nights'] = value.get('nights', 0)
			elif key == 'buttons' and isinstance(value, dict):
				# Extract button flags
				flattened_data['view_details'] = value.get('view_details', True)
				flattened_data['share'] = value.get('share', True)
				flattened_data['is_saved'] = value.get('save', True)
				flattened_data['regenerate_plan'] = value.get('regenerate_plan', True)
			else:
				flattened_data[key] = value
		
		# Add details as a JSON field
		flattened_data['details'] = details_data
		
		filtered_data = {k: v for k, v in flattened_data.items() if v != '' and v != '0'}
	else:
		# Handle flat structure (original format)
		filtered_data = {k: v for k, v in data.items() if v != '' and v != '0'}

	# Remove duplicate check by title
	title = filtered_data.get('title', None)
	if title is not None:
		if Trip.objects.filter(title__iexact=title, created_by=request.user).exists():
			return Response({'detail': f"Trip with title '{title}' already exists for this user."}, status=status.HTTP_400_BAD_REQUEST)

	serializer = TripSerializer(data=filtered_data)
	if serializer.is_valid():
		serializer.save(created_by=request.user)
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	else:
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=TripSerializer, responses=TripSerializer)
@api_view(['PUT'])
def updateTrip(request,pk):
	try:
		trip = Trip.objects.get(pk=pk)
		data = request.data

		# Store original is_shared state before update
		was_shared = trip.is_shared
		
		# detect if is_shared is being set true in this update
		incoming_is_shared = None
		if isinstance(data, dict) and 'is_shared' in data:
			incoming_is_shared = bool(data.get('is_shared'))

		serializer = TripSerializer(trip, data=data, partial=True)
		if serializer.is_valid():
			with transaction.atomic():
				updated_trip = serializer.save()

				# If trip is being shared now (was False, now True), create Post
				if incoming_is_shared and not was_shared:
					# avoid duplicate post creation: check if a matching shared post exists
					exists = Post.objects.filter(title=updated_trip.title, created_by=updated_trip.created_by, is_shared=True).exists()
					if not exists:
						post_data = {
							'title': updated_trip.title,
							'image_url': updated_trip.image_url,
							'location': updated_trip.location,
							'view_details': updated_trip.view_details,
							'share': updated_trip.share,
							'is_saved': updated_trip.is_saved,
							'is_shared': True,
							'regenerate_plan': updated_trip.regenerate_plan,
							'duration_days': updated_trip.duration_days,
							'duration_nights': updated_trip.duration_nights,
							'spots_count': updated_trip.spots_count,
							'categories': updated_trip.categories,
							'description': updated_trip.description,
							'summary_itinerary': updated_trip.summary_itinerary,
							'details': updated_trip.details,
							'created_by': updated_trip.created_by,
							'updated_by': updated_trip.updated_by,
						}
						Post.objects.create(**post_data)

			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"Trip id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=TripSerializer, responses=TripSerializer)
@api_view(['DELETE'])
def deleteTrip(request, pk):
	try:
		role = Trip.objects.get(pk=pk)
		role.delete()
		return Response({'detail': f'Trip id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Trip id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)

