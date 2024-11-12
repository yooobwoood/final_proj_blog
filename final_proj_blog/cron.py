from news.news_crawling import news_summary
from blog.views import generate_unique_slug
from blog.models import News, Subject, RelatedWord, Word, Word_Tag
from today_word.words700 import (
    initialize_rag_system,
    generate_answer,
    generate_response
)

def news_create():
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


def word_create():
    hybrid_retriever, tokenizer, model, llm_chain = initialize_rag_system()

    query = Subject.objects.filter(category='word', use_yn=False).order_by('?').values_list('title', flat=True).first()['title']

    unique_documents, reranked_documents = generate_answer(query, hybrid_retriever, tokenizer, model)
    response = generate_response(query, reranked_documents, llm_chain)

    tags = list(RelatedWord.objects.filter(origin_word=query).values_list('related_word', flat=True))

    Word(
        title=query,
        content=response,
    ).save()
    
    if tags:
        for t in tags:
            t = t.strip()
            existing_tag = Word_Tag.objects.filter(name=t).first()
            if existing_tag:
                continue
            else:
                tag = Word_Tag(name=t)
                tag.slug = generate_unique_slug(t)  # 고유 슬러그 생성 함수 사용
                tag.save()