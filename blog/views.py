from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.text import slugify
from django.shortcuts import get_object_or_404
from .models import Post, Tag, Comment
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from .forms import CommentForm

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt



class PostList(ListView):
    model = Post
    ordering = '-pk'
    paginate_by = 5

    def get_context_data(self, **kwargs):
        context = super(PostList, self).get_context_data(**kwargs)
        context['comment_form'] = CommentForm
        return context


class PostDetail(DetailView):
    model = Post

    def get_context_data(self, **kwargs):
        context = super(PostDetail, self).get_context_data()
        context['comment_form'] = CommentForm
        return context

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
            Q(title__contains=q) | Q(tags__name__contains=q)
        ).distinct()
        return post_list
    def get_context_data(self, **kwargs):
        context = super(PostSearch, self).get_context_data()
        q = self.kwargs['q']
        context['search_info'] = f'Search: {q}'
        return context

def tag_page(request, slug):
    tag = Tag.objects.get(slug=slug)
    post_list = tag.post_set.all()
    return render(
        request,
        'blog/post_list.html',
        {
            'post_list': post_list,
            'tag': tag,
        }
    )

# class PostCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
#     model = Post
#     fields = ['title', 'content', 'head_image']
#     template_name = 'blog/create_new_post.html'
#
#     def test_func(self):
#         return self.request.user.is_superuser or self.request.user.is_staff
#
#     def form_valid(self, form):
#         current_user = self.request.user
#         if current_user.is_authenticated and (current_user.is_staff or current_user.is_superuser):
#             form.instance.author = current_user
#             response = super(PostCreate, self).form_valid(form)
#
#             tags_str = self.request.POST.get('tags_str')
#             if tags_str:
#                 tags_str = tags_str.strip()
#                 tags_str = tags_str.replace(',', ';')
#                 tags_list = tags_str.split(';')
#                 for t in tags_list:
#                     t = t.strip()
#                     tag, is_tag_created = Tag.objects.get_or_create(name=t)
#                     if is_tag_created:
#                         tag.slug = slugify(t, allow_unicode=True)
#                         tag.save()
#                     self.object.tags.add(tag)
#
#             return response
#
#         else:
#             return redirect('/blog/')

def create_post(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        head_image = request.FILES.get("head_image")  # 이미지 파일 가져오기
        tags_str = request.POST.get("tags_str", "")

        # 새 Post 인스턴스 생성
        post = Post.objects.create(
            title=title,
            content=content,
            head_image=head_image,  # 이미지 저장
            author=request.user,
        )

        # 태그 저장
        if tags_str:
            tags_list = tags_str.replace(',', ';').split(';')
            for tag_name in tags_list:
                tag, _ = Tag.objects.get_or_create(name=tag_name.strip())
                post.tags.add(tag)

        return redirect(post.get_absolute_url())  # 게시물 상세 페이지로 리디렉션

    return render(request, "blog/create_new_post.html")



