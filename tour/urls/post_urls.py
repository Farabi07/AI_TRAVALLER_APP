
from django.urls import path
from tour.views import post_views as views


urlpatterns = [
	path('api/v1/post/all/', views.getAllPost),

	path('api/v1/post/without_pagination/all/', views.getAllPostWithoutPagination),

	path('api/v1/post/<int:pk>', views.getAPost),
	# path('api/v1/post/search/', views.searchPost),

	path('api/v1/post/create/', views.createPost),

	path('api/v1/post/comment/<int:pk>', views.createPostComment),

	# Posts liked by current user
	path('api/v1/post/liked/', views.getLikedPosts),
	path('api/v1/post/liked/without_pagination/', views.getLikedPostsWithoutPagination),

	# Like toggle
	path('api/v1/post/like/<int:pk>', views.toggle_post_like),

	path('api/v1/post/update/<int:pk>', views.updatePost),

	path('api/v1/post/delete/<int:pk>', views.deletePost),

]