from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('search/<str:q>/', views.PostSearch.as_view(), name='post_search'),
    path('delete_comment/<int:pk>/', views.delete_comment),
    path('update_comment/<int:pk>/', views.CommentUpdate.as_view()),
    path('update_post/<int:pk>/', views.PostUpdate.as_view(), name='post_update'),
    path('create_post/', views.PostCreate.as_view(), name='post_create'),  # create_post에서 PostCreate로 변경
    path('<int:pk>/new_comment/', views.new_comment),
    path('<int:pk>/', views.PostDetail.as_view(), name='post_detail'),
    path('accounts/', include('allauth.urls')),
    path('', views.PostList.as_view(), name='post_list'),
    path('generate_image/', views.generate_image, name='generate_image'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)