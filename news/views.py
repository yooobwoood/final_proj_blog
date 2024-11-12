from lib2to3.fixes.fix_input import context
from django.shortcuts import redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from blog.models import News
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from blog.forms import CommentForm
from collections import defaultdict
from django.utils import timezone


class NewsList(ListView):
    model = News
    template_name = 'news/news_list.html'
    context_object_name = 'news_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 날짜별 뉴스 데이터를 딕셔너리로 그룹화
        news_dict = defaultdict(list)

        for news in News.objects.all():
            date_key = news.created_at.strftime('%Y-%m-%d')
            news_dict[date_key].append({'title': news.title, 'url': news.get_absolute_url()})
        
        # JSON 형식으로 템플릿에 전달
        context['news_dict'] = news_dict
        
        # 오늘 날짜의 뉴스 필터링
        today = timezone.now().date()
        today_news = News.objects.filter(created_at__date=today)
        
        # 템플릿에 전달
        context['today_news'] = today_news

        return context

class NewsDetail(DetailView):
    model = News
    template_name = 'news/news_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 오늘 날짜의 뉴스 필터링
        today = timezone.now().date()
        today_news = News.objects.filter(created_at__date=today)
        
        # 템플릿에 전달
        context['today_news'] = today_news
        context['comment_form'] = CommentForm
        return context


class NewsUpdate(LoginRequiredMixin, UpdateView):
    model = News
    fields = ['title', 'content']

    template_name = 'blog/news_update_form.html'

    def get_context_data(self, **kwargs):
        context = super(NewsUpdate, self).get_context_data()
        return context

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user == self.get_object().author:
            return super(NewsUpdate, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied

    def form_valid(self, form):
        response = super(NewsUpdate, self).form_valid(form)
        return response


class NewsSearch(NewsList):
    paginate_by = None
    def get_queryset(self):
        q = self.kwargs['q']
        post_list = News.objects.filter(
            Q(title__contains=q)
        ).distinct()
        return post_list
    def get_context_data(self, **kwargs):
        context = super(NewsSearch, self).get_context_data()
        q = self.kwargs['q']
        context['search_info'] = f'Search: {q}'
        return context