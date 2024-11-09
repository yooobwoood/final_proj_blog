from news.news_crawling import news_summary
from news.models import News

def NewsCreate():
    post_title = ""
    post_body = ""

    news_arr = news_summary()

    for news in news_arr:
        post_title += f"\#{news['word']} "
        post_body += f"##{news['title']}\n{news['body']}\n[{news['origin_title']}]({news['link']})\n\n\n"

    post_title = post_title.strip()
    post_body = post_body.strip()

    News(
        title = post_title,
        content = post_body
    ).save()
