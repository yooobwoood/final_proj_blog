from django.urls import path, include

from . import views

urlpatterns = [
    path('', views.NewsList.as_view(), name='news_list'),
    path('<int:pk>/', views.NewsDetail.as_view(), name='news_detail'),
    path('update_post/<int:pk>/', views.NewsUpdate.as_view(), name='news_update'),
    path('search/<str:q>/', views.NewsSearch.as_view(), name='news_search'),
]