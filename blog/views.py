from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.text import slugify
from django.shortcuts import get_object_or_404
from .models import Post, Tag, Comment, News, Subject
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from .forms import CommentForm
from django.utils import timezone
from django.utils.text import slugify
from .easystory import (
    initialize_rag_system,
    generate_answer,
    generate_debug_output,
    generate_response
)
from django.http import JsonResponse

from django.conf import settings
from django.http import JsonResponse
from .dalle import save_gen_img, OpenAI, BadRequestError
import json
import os
from dotenv import load_dotenv
from django.core.files import File
from urllib.request import urlopen
from tempfile import NamedTemporaryFile

load_dotenv()

# RAG 시스템 초기화
hybrid_retriever, tokenizer, model, llm_chain = initialize_rag_system()

class PostList(ListView):
    model = Post
    ordering = '-pk'
    paginate_by = 5

    def get_context_data(self, **kwargs):
        context = super(PostList, self).get_context_data(**kwargs)
        # 오늘 날짜의 뉴스 필터링
        today = timezone.now().date()
        today_news = News.objects.filter(created_at__date=today)
        # 템플릿에 전달
        context['today_news'] = today_news
        context['comment_form'] = CommentForm
        return context
    
class PostDetail(DetailView):
    model = Post

    def get_context_data(self, **kwargs):
        context = super(PostDetail, self).get_context_data()
        # 오늘 날짜의 뉴스 필터링
        today = timezone.now().date()
        today_news = News.objects.filter(created_at__date=today)
        # 템플릿에 전달
        context['today_news'] = today_news
        context['comment_form'] = CommentForm
        return context

    



def new_comment(request, pk):
    if request.user.is_authenticated:
        post = get_object_or_404(Post, pk=pk)
        if request.method == 'POST':
            comment_form = CommentForm(request.POST)

            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.post = post
                comment.author = request.user
                comment.save()
                return redirect(comment.get_absolute_url())
        else:
            return redirect(post.get_absolute_url())
    else:
        raise PermissionDenied

class CommentUpdate(LoginRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user == self.get_object().author:
            return super(CommentUpdate, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied

def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    post = comment.post
    if request.user.is_authenticated and request.user == comment.author:
        comment.delete()
        return redirect(post.get_absolute_url())
    else:
        raise PermissionDenied

class PostSearch(PostList):
    paginate_by = None

    def get_queryset(self):
        q = self.kwargs['q']
        post_list = Post.objects.filter(
            Q(title__contains=q)
        ).distinct()
        return post_list

    def get_context_data(self, **kwargs):
        context = super(PostSearch, self).get_context_data()
        q = self.kwargs['q']
        context['search_info'] = f'Search: {q}'
        return context


def generate_unique_slug(name):
    slug = slugify(name, allow_unicode=True)
    unique_slug = slug
    number = 1
    while Tag.objects.filter(slug=unique_slug).exists():
        unique_slug = f"{slug}-{number}"
        number += 1
    return unique_slug

class PostUpdate(LoginRequiredMixin, UpdateView):
    model = Post
    fields = ['title', 'content', 'head_image']
    template_name = 'blog/post_update_form.html'

    def get_context_data(self, **kwargs):
        context = super(PostUpdate, self).get_context_data()
        if self.object.tags.exists():
            tags_str_list = list()
            for t in self.object.tags.all():
                tags_str_list.append(t.name)
            context['tags_str_default'] = '; '.join(tags_str_list)
        return context

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user == self.get_object().author:
            return super(PostUpdate, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied

    def form_valid(self, form):
        response = super(PostUpdate, self).form_valid(form)
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



class PostCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Post
    fields = ['title', 'content', 'head_image']
    template_name = 'blog/create_new_post.html'

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def form_valid(self, form):
        current_user = self.request.user
        if current_user.is_authenticated and (current_user.is_staff or current_user.is_superuser):
            form.instance.author = current_user

            # hidden input에서 이미지 URL 가져오기
            generated_image_url = self.request.POST.get('generated_image_url')
            if generated_image_url:
                # URL에서 이미지를 열어 임시 파일로 저장한 후 head_image에 첨부
                img_temp = NamedTemporaryFile(delete=True)
                img_temp.write(urlopen(generated_image_url).read())
                img_temp.flush()
                # 파일 이름을 지정하여 저장 (경로를 제거하고 파일명만 사용)
                file_name = os.path.basename(generated_image_url)
                form.instance.head_image.save(file_name, File(img_temp), save=False)

            response = super(PostCreate, self).form_valid(form)

            query = self.request.session.get('query')

            # Subject 테이블 업데이트
            title_instance = Subject.objects.filter(title=query).first()
            if title_instance:
                title_instance.use_yn = True
                title_instance.save()

            # 태그 추가
            tags_str = self.request.POST.get('tags_str')
            if tags_str:
                tags_str = tags_str.strip().replace(',', ';')
                tags_list = tags_str.split(';')
                for t in tags_list:
                    t = t.strip()
                    existing_tag = Tag.objects.filter(name=t).first()
                    if existing_tag:
                        tag = existing_tag
                    else:
                        tag = Tag(name=t)
                        tag.slug = generate_unique_slug(t)  # 고유 슬러그 생성 함수 사용
                        tag.save()
                    self.object.tags.add(tag)
            return response
        else:
            return redirect('/blog/')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # use_yn=False인 질문 중 랜덤 선택
        query = Subject.objects.filter(category='post', use_yn=False).order_by('?').values('title').first()['title']
        context['title'] = query
        self.request.session['query'] = query

        if query:
            unique_documents, reranked_documents = generate_answer(query, hybrid_retriever, tokenizer, model)
            debug_output = generate_debug_output(unique_documents, reranked_documents)
            response = generate_response(query, reranked_documents, llm_chain)
            context['response'] = response
            context['debug_output'] = debug_output
        return context

    def get(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and 'query' in request.GET:
            query = self.request.session.get('query')
            unique_documents, reranked_documents = generate_answer(query, hybrid_retriever, tokenizer, model)
            debug_output = generate_debug_output(unique_documents, reranked_documents)
            response = generate_response(query, reranked_documents, llm_chain)
            return JsonResponse({
                "response": response,
                "debug_output": debug_output
            })
        return super().get(request, *args, **kwargs)
    

def generate_image(request):
    if request.method == "POST":
        data = json.loads(request.body)
        txt_response = data.get("txt_response", "")
        client = OpenAI(api_key=os.getenv("OPENAI_KEY"))

        try:
            filename = save_gen_img(client, txt_response)
            file_url = request.build_absolute_uri(os.path.join(settings.MEDIA_URL, 'generated_images', filename))
        except BadRequestError:
            filename = save_gen_img(client, "시장 경제 활동")
            file_url = request.build_absolute_uri(os.path.join(settings.MEDIA_URL, 'generated_images', filename))

        return JsonResponse({"filename": filename, "file_url": file_url})    