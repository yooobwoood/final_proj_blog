from bs4 import BeautifulSoup
import requests
import datetime
from datetime import timedelta
from openai import OpenAI
from dotenv import load_dotenv
import os

def news_crawl():
    today_article = []

    today = datetime.date.today()
    yesterday = today - timedelta(days=1)
    year = yesterday.year
    month = yesterday.month
    day = yesterday.day

    print('requests get')
    response = requests.get(f"https://media.naver.com/press/055/ranking?type=section&date={year}{month}{day}")


    soup = BeautifulSoup(response.text, 'html.parser')
    li_list = soup.select('#ct > div.press_ranking_home > div:nth-child(4) > ul > li')

    for li in li_list:
        each_article = {}
        link = li.select_one('a').attrs['href']
        
        article = requests.get(link)
        arti_soup = BeautifulSoup(article.text, 'html.parser')

        title = arti_soup.select_one('#title_area > span').text.strip()
        body = arti_soup.select_one('article#dic_area').text.strip()

        each_article['origin_title'] = title
        each_article['origin_body'] = body
        each_article['link'] = link
        each_article['news_date'] = f"{year}{month}{day}"

        today_article.append(each_article)

    print('return response')
    return today_article


def news_summary():
    today_article = news_crawl()

    # .env 파일 로드
    load_dotenv()

    # OpenAI API 키 로드
    openai_api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=openai_api_key)

    article_body = []
    news_result = []

    for i in range(len(today_article)):
        article_body.append(today_article[i]['origin_body'])

    print('openai start')
    for j in article_body:
        response = client.chat.completions.create(
            model="ft:gpt-4o-2024-08-06:skn2-2:news-crawling:AObgFq9i",
            messages=[
            {"role": "system", "content": """당신은 사용자가 입력한 뉴스를 요약해주는 유용한 AI입니다.
                사용자에게 친절하고 다정한 말투를 사용하세요.
            
                사용자가 입력한 내용을 바탕으로 아래 3가지를 수행하세요.
            
                    1. 요약:사용자가 입력한 뉴스를 요약해주세요.
            
                    2. 제목:요약 내용을 바탕으로 제목을 생성해주세요. 제목은 따옴표나 쌍따옴표로 감싸지 말고 텍스트로만 출력해주세요.
            
                    3. 단어:요약 내용을 대표할 수 있는 단어 1개를 뉴스에서 추출해주세요. 단어는 따옴표나 쌍따옴표로 감싸지 말고 텍스트로만 출력해주세요.
            
                반드시 사용자가 입력한 내용만을 바탕으로 요청사항을 수행해야합니다.
                사용자의 입력 내용이 특정 회사의 상황을 나타내고 있을 경우 가장 중요한 단어는 그 회사의 이름이어야 합니다.
                수행한 결과들을 각각 순서대로 번호만 붙여서 출력하세요."""},
            {"role": "user", "content": j}, 
            ]
        )

        news_result.append(response.choices[0].message.content)
    
    print('openai end')
    for i in range(len(news_result)):
        today_article[i]['body'] = news_result[i].split('\n\n')[0].split(': ')[1]
        today_article[i]['title'] = news_result[i].split('\n\n')[1].split(': ')[1]
        today_article[i]['word'] = news_result[i].split('\n\n')[2].split(': ')[1]
    
    return today_article