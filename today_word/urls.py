from django.urls import path
from . import views

urlpatterns=[
    path('search/<str:q>/', views.WordSearch.as_view(), name='word_search'),
    path('update_post/<int:pk>/', views.WordUpdate.as_view()),
    path('create_post/', views.WordCreate.as_view(), name='word_create'),
    path('tag/<str:slug>/', views.tag_page),
    path('<int:pk>/', views.WordDetail.as_view()),
    path('', views.WordList.as_view()),

]