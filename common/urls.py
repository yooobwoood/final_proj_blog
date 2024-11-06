from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


app_name = 'common'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='common/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup, name='signup'),
    path('profile_update/', views.profile_update, name='profile_update'),  # 추가된 URL
    path('change_password/', views.change_password, name='change_password'),  # 비밀번호 변경 경로
    path('delete_account/', views.delete_account, name='delete_account'),  # 회원 탈퇴 경로 추가

]
