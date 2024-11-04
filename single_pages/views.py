from django.shortcuts import render
from blog.models import Post, Word

def landing(request):
    recent_posts = Post.objects.order_by('-pk')[:3]
    recent_word = Word.objects.order_by('-pk')[:1]

    return render(
        request,
        'single_pages/landing.html',
        {
            'recent_posts': recent_posts,
            'recent_word': recent_word,
        }
    )

def about_me(request):
    return render(
        request,
        'single_pages/about_me.html'
    )
