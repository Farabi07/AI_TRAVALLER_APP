from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from tour.models import Post, Trip
from tour.serializers import PostSerializer, PostListSerializer, TripListSerializer
from tour.serializers import PostCommentSerializer
from tour.models import PostComment
# from authentication.filters import PostFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from drf_spectacular.utils import  extend_schema, OpenApiParameter
from commons.pagination import Pagination
from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError




# Create your views here.

@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=PostSerializer,
	responses=PostSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllPost(request):
	from django.db.models import Count
	# Only return posts created by the current user
	# Annotate like_count for efficiency (avoids N+1 queries)
	posts = Post.objects.all().annotate(like_count=Count('likes'))
	total_elements = posts.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	posts = pagination.paginate_data(posts)

	serializer = PostListSerializer(posts, many=True, context={'request': request})

	response = {
		'posts': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	# include shared trips (publicly shared) so frontend can show them alongside posts
	try:
		shared_qs = Trip.objects.filter(is_shared=True).order_by('-created_at')
		response['shared_trips'] = TripListSerializer(shared_qs, many=True, context={'request': request}).data
	except Exception:
		response['shared_trips'] = []

	return Response(response, status=status.HTTP_200_OK)




@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=PostSerializer,
	responses=PostSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getAllPostWithoutPagination(request):
	from django.db.models import Count
	# Annotate like_count for efficiency (avoids N+1 queries)
	posts = Post.objects.all().annotate(like_count=Count('likes'))
	serializer = PostListSerializer(posts, many=True, context={'request': request})
	return Response({'posts': serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getLikedPosts(request):
	"""Paginated list of posts liked by current user.
	Query params: page, size
	"""
	from django.db.models import Count

	posts = Post.objects.filter(likes__user=request.user).annotate(like_count=Count('likes')).distinct()
	total_elements = posts.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	posts = pagination.paginate_data(posts)

	serializer = PostListSerializer(posts, many=True, context={'request': request})

	response = {
		'posts': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}
	return Response(response, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getLikedPostsWithoutPagination(request):
	"""Return all posts liked by current user (no pagination)."""
	from django.db.models import Count
	posts = Post.objects.filter(likes__user=request.user).annotate(like_count=Count('likes')).distinct()
	serializer = PostListSerializer(posts, many=True, context={'request': request})
	return Response({'posts': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=PostSerializer, responses=PostSerializer)
@api_view(['GET'])
def getAPost(request, pk):
	try:
		posts = Post.objects.get(pk=pk)
		serializer = PostSerializer(posts, context={'request': request})
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Post id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




# @extend_schema(request=PostSerializer, responses=PostSerializer)
# @api_view(['GET'])
# # @permission_classes([IsAuthenticated])
# # @has_permissions([PermissionEnum.PRODUCT_DETAILS.name])
# def searchPost(request):

# 	posts = PostFilter(request.GET, queryset=Post.objects.all())
# 	posts = posts.qs

# 	print('posts: ', posts)

# 	total_elements = posts.count()

# 	page = request.query_params.get('page')
# 	size = request.query_params.get('size')

# 	# Pagination
# 	pagination = Pagination()
# 	pagination.page = page
# 	pagination.size = size
# 	posts = pagination.paginate_data(posts)

# 	serializer = PostListSerializer(posts, many=True)

# 	response = {
# 		'posts': serializer.data,
# 		'page': pagination.page,
# 		'size': pagination.size,
# 		'total_pages': pagination.total_pages,
# 		'total_elements': total_elements,
# 	}

# 	if len(posts) > 0:
# 		return Response(response, status=status.HTTP_200_OK)
# 	else:
# 		return Response({'detail': f"There are no posts matching your search"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=PostSerializer, responses=PostSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createPost(request):
	data = request.data
	# Merge request.data and request.FILES so file fields are passed to the serializer
	filtered_data = {k: v for k, v in data.items() if v != '' and v != '0'}
	for f_key, f_val in request.FILES.items():
		filtered_data[f_key] = f_val

	# Remove duplicate check by name, use title instead
	title = filtered_data.get('title', None)
	if title is not None:
		if Post.objects.filter(title__iexact=title, created_by=request.user).exists():
			return Response({'detail': f"Post with title '{title}' already exists for this user."}, status=status.HTTP_400_BAD_REQUEST)

	# pass request in context so serializer can build absolute file URLs when needed
	serializer = PostSerializer(data=filtered_data, context={'request': request})
	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	else:
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=PostSerializer, responses=PostSerializer)
@api_view(['PUT'])
def updatePost(request,pk):
	try:
		posts = Post.objects.get(pk=pk)
		data = request.data
		serializer = PostSerializer(posts, data=data, context={'request': request})
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"posts id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=PostSerializer, responses=PostSerializer)
@api_view(['DELETE'])
def deletePost(request, pk):
	try:
		posts = Post.objects.get(pk=pk)
		posts.delete()
		return Response({'detail': f'Post id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Post id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)



@extend_schema(request=PostCommentSerializer, responses=PostCommentSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createPostComment(request, pk):
	"""Create a comment for a post (pk). Body: {"text": "..."} """
	try:
		post = Post.objects.get(pk=pk)
	except ObjectDoesNotExist:
		return Response({'detail': f"Post id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)

	text = request.data.get('text')
	if not text:
		return Response({'detail': 'Comment text is required'}, status=status.HTTP_400_BAD_REQUEST)

	comment = PostComment.objects.create(post=post, user=request.user, text=text)
	serializer = PostCommentSerializer(comment, context={'request': request})
	return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_post_like(request, pk):
	"""Toggle like for post with id=pk by request.user.
	Returns {"liked": bool, "like_count": int}
	"""
	user = request.user
	post = get_object_or_404(Post, pk=pk)
	liked = False
	try:
		with transaction.atomic():
			like_obj, created = post.likes.get_or_create(user=user)
			if not created:
				# already liked -> unlike
				like_obj.delete()
				liked = False
			else:
				liked = True
	except IntegrityError:
		# fallback in race conditions
		liked = post.likes.filter(user=user).exists()
	like_count = post.likes.count()
	return Response({'liked': liked, 'like_count': like_count}, status=status.HTTP_200_OK)
