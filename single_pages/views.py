from django.shortcuts import render
from blog.models import Post, Word, News
from django.utils import timezone

def landing(request):
    recent_posts = Post.objects.order_by('-pk')[:3]
    recent_word = Word.objects.order_by('-pk')[:1]

    today = timezone.now().date()
    today_news = News.objects.filter(created_at__date=today)

    return render(
        request,
        'single_pages/landing.html',
        {
            'recent_posts': recent_posts,
            'recent_word': recent_word,
            'today_news' : today_news,
        }
    )

def about_me(request):
    return render(
        request,
        'single_pages/about_me.html'
    )
