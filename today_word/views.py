from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.text import slugify
from blog.models import Word, Word_Tag, News
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone
from .words700 import (
    initialize_rag_system,
    generate_answer,
    generate_debug_output,
    generate_response
)
from django.http import JsonResponse
import os

# OpenAI API 키 가져오기
openai_api_key = os.getenv("OPENAI_API_KEY")

# RAG 시스템 초기화
hybrid_retriever, tokenizer, model, llm_chain = initialize_rag_system()

class WordList(ListView):
    model = Word
    ordering = '-pk'
    paginate_by = 5

    def get_context_data(self, **kwargs):
        context = super(WordList, self).get_context_data(**kwargs)
        context['tags'] = Word_Tag.objects.all()
        # 오늘 날짜의 뉴스 필터링
        today = timezone.now().date()
        today_news = News.objects.filter(created_at__date=today)
        # 템플릿에 전달
        context['today_news'] = today_news
        return context

class WordDetail(DetailView):
    model = Word

    def get_context_data(self, **kwargs):
        context = super(WordDetail, self).get_context_data()
        context['tags'] = Word_Tag.objects.all()
        # 오늘 날짜의 뉴스 필터링
        today = timezone.now().date()
        today_news = News.objects.filter(created_at__date=today)
        # 템플릿에 전달
        context['today_news'] = today_news
        return context

class WordCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Word
    fields = ['title', 'content']
    template_name = 'today_word/create_new_word.html'

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def form_valid(self, form):
        current_user = self.request.user
        if current_user.is_authenticated and (current_user.is_staff or current_user.is_superuser):
            form.instance.author = current_user

            # Save the form to create self.object
            response = super(WordCreate, self).form_valid(form)

            # Now that self.object is created, you can add tags to it
            tags_str = self.request.POST.get('tags_str')
            if tags_str:
                tags_str = tags_str.strip().replace(',', ';')
                tags_list = tags_str.split(';')
                for t in tags_list:
                    t = t.strip()
                    tag, is_tag_created = Word_Tag.objects.get_or_create(name=t)
                    if is_tag_created:
                        tag.slug = slugify(t, allow_unicode=True)
                        tag.save()
                    self.object.tags.add(tag)

            return response
        else:
            return redirect('/today_word/')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("query", "")
        if query:
            unique_documents, reranked_documents = generate_answer(query, hybrid_retriever, tokenizer, model)
            debug_output = generate_debug_output(unique_documents, reranked_documents)
            response = generate_response(query, reranked_documents, llm_chain)
            context['response'] = response
            context['debug_output'] = debug_output
        return context

    def get(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and 'query' in request.GET:
            query = request.GET.get('query', "")
            unique_documents, reranked_documents = generate_answer(query, hybrid_retriever, tokenizer, model)
            debug_output = generate_debug_output(unique_documents, reranked_documents)
            response = generate_response(query, reranked_documents, llm_chain)
            return JsonResponse({
                "response": response,
                "debug_output": debug_output
            })
        return super().get(request, *args, **kwargs)

class WordUpdate(LoginRequiredMixin, UpdateView):
    model = Word
    fields = ['title', 'content']

    template_name = 'blog/word_update_form.html'

    def get_context_data(self, **kwargs):
        context = super(WordUpdate, self).get_context_data()
        if self.object.tags.exists():
            tags_str_list = list()
            for t in self.object.tags.all():
                tags_str_list.append(t.name)
            context['tags_str_default'] = '; '.join(tags_str_list)
        return context

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user == self.get_object().author:
            return super(WordUpdate, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied

    def form_valid(self, form):
        response = super(WordUpdate, self).form_valid(form)
        self.object.tags.clear()
        tags_str = self.request.POST.get('tags_str')
        if tags_str:
            tags_str = tags_str.strip()
            tags_str = tags_str.replace(',', ';')
            tags_list = tags_str.split(';')
            for t in tags_list:
                t = t.strip()
                tag, is_tag_created = Word_Tag.objects.get_or_create(name=t)
                if is_tag_created:
                    tag.slug = slugify(t, allow_unicode=True)
                    tag.save()
                self.object.tags.add(tag)
        return response

class WordSearch(WordList):
    paginate_by = None
    def get_queryset(self):
        q = self.kwargs['q']
        post_list = Word.objects.filter(
            Q(title__contains=q)
        ).distinct()
        return post_list
    def get_context_data(self, **kwargs):
        context = super(WordSearch, self).get_context_data()
        q = self.kwargs['q']
        context['search_info'] = f'Search: {q}'
        return context

def tag_page(request, slug):
    tag = Word_Tag.objects.get(slug=slug)
    post_list = Word.objects.filter(tags=tag)
    return render(
        request,
        'blog/word_list.html',
        {
            'word_list': post_list,
            'tag': tag,
        }
    )