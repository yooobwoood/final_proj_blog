from lib2to3.fixes.fix_input import context
from django.shortcuts import redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.text import slugify
from blog.models import Tag, News
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
        if self.object.tags.exists():
            tags_str_list = list()
            for t in self.object.tags.all():
                tags_str_list.append(t.name)
            context['tags_str_default'] = '; '.join(tags_str_list)
        return context

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user == self.get_object().author:
            return super(NewsUpdate, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied

    def form_valid(self, form):
        response = super(NewsUpdate, self).form_valid(form)
        self.object.tags.clear()
        tags_str = self.request.POST.get('tags_str')
        if tags_str:
            tags_str = tags_str.strip()
            tags_str = tags_str.replace(',', ';')
            tags_list = tags_str.split(';')
            for t in tags_list:
                t = t.strip()
                tag, is_tag_created = Tag.objects.get_or_create(name=t)
                if is_tag_created:
                    tag.slug = slugify(t, allow_unicode=True)
                    tag.save()
                self.object.tags.add(tag)
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


class NewsCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = News
    fields = ['title', 'content']
    template_name = 'news/create_new_news.html'  # 생성한 템플릿 파일을 지정

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def form_valid(self, form):
        current_user = self.request.user
        if current_user.is_authenticated and (current_user.is_staff or current_user.is_superuser):
            form.instance.author = current_user

            # Save the form to create self.object
            response = super(NewsCreate, self).form_valid(form)

            return response
        else:
            return redirect('/news/')

