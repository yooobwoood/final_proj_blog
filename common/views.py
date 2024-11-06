from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from common.forms import UserForm, UserUpdateForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User

def logout_view(request):
    logout(request)
    return redirect('/')

def signup(request):
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)  # 사용자 인증
            login(request, user)  # 로그인
            return redirect('/')
    else:
        form = UserForm()
    return render(request, 'common/signup.html', {'form': form})


@login_required
def profile_update(request):
    form = UserUpdateForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '회원 정보가 수정되었습니다.')
        return redirect('/')  # 랜딩 페이지로 리다이렉트
    return render(request, 'common/profile_update.html', {
        'form': form,
    })
@login_required
def change_password(request):
    password_form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and password_form.is_valid():
        user = password_form.save()
        update_session_auth_hash(request, user)
        messages.success(request, '비밀번호가 성공적으로 변경되었습니다.')
        return redirect('/')
    return render(request, 'common/change_password.html', {
        'password_form': password_form,
    })
@login_required
def delete_account(request):
    if request.method == "POST":
        user = request.user
        user.is_active = False  # 사용자를 비활성화
        user.save()
        messages.success(request, "회원 탈퇴가 완료되었습니다.")
        logout(request)  # 로그아웃 처리
        return redirect('/')  # 홈 페이지로 리다이렉트
    return render(request, 'common/delete_account.html')