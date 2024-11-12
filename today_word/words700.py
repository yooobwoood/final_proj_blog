import pickle
import torch
import pandas as pd

from konlpy.tag import Kkma
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_teddynote.retrievers import EnsembleRetriever, EnsembleMethod
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI

import warnings
warnings.filterwarnings('ignore')

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from dotenv import load_dotenv
load_dotenv()

from final_proj_blog.utils import download_index_from_s3, load_index

if not os.path.isdir('./index'):
    os.mkdir('./index')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "700words.csv")
FAISS_INDEX_PATH = os.path.join(BASE_DIR, "index", "700words_faiss_index.pkl")
BM25_INDEX_PATH = os.path.join(BASE_DIR, "index", "700words_bm25_index.pkl")
S3_FAISS_INDEX = "700words_faiss_index.pkl"
S3_BM25_INDEX = "700words_bm25_index.pkl"

# Load & Process Documents
def load_csv_as_documents(file_path):
    df = pd.read_csv(file_path, encoding='utf-8')
    documents = []
    for _, row in df.iterrows():
        title = row['title'].strip() if pd.notna(row['title']) else ""
        content = row['content'].strip() if pd.notna(row['content']) else ""
        combined_context = f"단어: {title}\n설명: {content}"
        doc = Document(
            page_content=combined_context,
            metadata={
                'title': title,
                'related_keyword': row.get('related_keyword', '').strip() if pd.notna(row['related_keyword']) else "",
                'doc_id': _
            }
        )
        documents.append(doc)
    return documents

# kkma 한국어 형태소 분리기
kkma = Kkma()

def kkma_tokenize(text):
    return [token for token in kkma.morphs(text)]

# Load or create index 
def load_or_create_index(documents, faiss_index_path, bm25_index_path):
    if not os.path.exists(faiss_index_path):
        print('s3 download start')
        download_index_from_s3(S3_FAISS_INDEX, faiss_index_path)
    if not os.path.exists(bm25_index_path):
        print('s3 download start')
        download_index_from_s3(S3_BM25_INDEX, bm25_index_path)

    if os.path.exists(faiss_index_path) and os.path.exists(bm25_index_path):
        faiss_index = load_index(faiss_index_path)
        bm25_index = load_index(bm25_index_path)
    else:
        embedding_model = HuggingFaceEmbeddings(
            model_name='paraphrase-multilingual-MiniLM-L12-v2',
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True},
        )
        faiss_index = FAISS.from_documents(documents, embedding_model).as_retriever(search_kwargs={"k": 5})
        with open(faiss_index_path, 'wb') as f:
            pickle.dump(faiss_index, f)
        
        bm25_index = BM25Retriever.from_documents(documents, preprocess_func=kkma_tokenize)
        bm25_index.k = 5
        with open(bm25_index_path, 'wb') as f:
            pickle.dump(bm25_index, f)
    
    return faiss_index, bm25_index


# Hybrid Retriever CC method Setup
def create_hybrid_retriever(faiss_index, bm25_index):
    weights = [0.93, 0.07]
    hybrid_retriever = EnsembleRetriever(
        retrievers=[faiss_index, bm25_index],
        weights=weights,
        method=EnsembleMethod.CC
    )
    return hybrid_retriever

# Initialize Reranker
def initialize_reranker(model_path="Dongjin-kr/ko-reranker"):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    return tokenizer, model

# Rerank Function
def rerank(query, retrieved_documents, tokenizer, model, top_k=3):
    pairs = [[query, doc.page_content] for doc in retrieved_documents]
    inputs = tokenizer(pairs, padding=True, truncation=True, return_tensors='pt', max_length=256)
    with torch.no_grad():
        scores = model(**inputs, return_dict=True).logits.view(-1).float()
    reranked_docs = sorted(zip(retrieved_documents, scores), key=lambda x: x[1], reverse=True)
    return reranked_docs[:top_k]

# Optimize Context
def optimize_context(reranked_docs, max_tokens=6000):
    context = ""
    for doc, score in reranked_docs:
        if len(context) + len(doc.page_content) > max_tokens:
            break
        context += doc.page_content + "\n\n"
    return context.strip()

# Prompt & LLM Initialization
def initialize_llm_chain():
    prompt_template = PromptTemplate(
        input_variables=["query", "retrieved_contents"],
        template="""
        당신의 역할은 경제 용어에 대해 친절하고 쉽게 이해할 수 있는 설명을 제공하는 것입니다.
        당신은 경제 지식이 없거나 경제 개념을 쉽게 배우고 싶은 사람들을 대상으로 '오늘의 단어' 포스팅을 작성합니다.

        먼저 단어의 정의를 상세하게 설명해 주고, 일상 생활에 적용할 수 있는 관련 예시를 하나 간단하게 들어주세요.

        마지막으로 이 용어를 이해하는 것이 왜 중요한지 요약하고 글을 마무리해 주세요.
        경제 지식이 전혀 없는 사람도 쉽게 이해하고 흥미롭게 읽을 수 있도록 친근하고 쉽게 작성해 주세요.

        # 주의사항:
        1. 문서의 내용을 기반으로만 글을 작성하세요. 내용을 지어내거나 사실과 다르게 작성하지 마세요.
        2. 만약 설명할 수 없는 부분이 있다면, '모르겠습니다'라고 답하세요.
        3. 모든 제목은 #나 ## 같은 Markdown 표시 없이 굵은 글씨(**)로 나타나야 합니다. 예를 들어'## 경기는'는 '**경기**는'로 표시합니다.
        4. 본문에는 일반 텍스트 형식을 사용하고, 필요할 경우 단어에만 굵은 글씨를 사용해주세요.
        5. 제목을 제외하여 주세요.

        이제 주제에 맞게 블로그 글을 작성해 주세요.
        질문: {query}
        단락: {retrieved_contents}
        답변:
        """
    )
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    return LLMChain(llm=llm, prompt=prompt_template)

def initialize_rag_system():
    documents = load_csv_as_documents(DATA_PATH)
    faiss_index, bm25_index = load_or_create_index(documents, FAISS_INDEX_PATH, BM25_INDEX_PATH)
    hybrid_retriever = create_hybrid_retriever(faiss_index, bm25_index)
    tokenizer, model = initialize_reranker()
    llm_chain = initialize_llm_chain()
    return hybrid_retriever, tokenizer, model, llm_chain

# Main Query Processing Function (Retrieve and Rerank)
def generate_answer(query, hybrid_retriever, tokenizer, model, top_k_retrieve=5, top_k_rerank=3):
    # Step 1: Retrieve documents
    retrieved_documents = hybrid_retriever.invoke(query)

    # Filter top-k retrieved documents
    unique_documents = []
    seen = set()
    for doc in retrieved_documents:
        if doc.page_content not in seen:
            unique_documents.append(doc)
            seen.add(doc.page_content)
        if len(unique_documents) == top_k_retrieve:
            break

    # Step 2: Rerank documents
    reranked_documents = rerank(query, unique_documents, tokenizer, model, top_k=top_k_rerank)
    return unique_documents, reranked_documents

# Generate Debug Output
def generate_debug_output(unique_documents, reranked_documents):
    debug_output = "최종 Retrieve 단계에서 검색된 문서:\n--------------------------------------------------\n"
    for i, doc in enumerate(unique_documents, 1):
        debug_output += f"문서 {i}:\n내용: {doc.page_content[:100]}...\n\n"

    debug_output += "\nReranker를 통해 재정렬된 문서:\n--------------------------------------------------\n"
    for i, (doc, score) in enumerate(reranked_documents, 1):
        debug_output += f"문서 {i} (점수: {score}):\n내용: {doc.page_content[:100]}...\n\n"

    return debug_output

# Generate Final Response
def generate_response(query, reranked_documents, llm_chain):
    optimized_context = optimize_context(reranked_documents)
    response = llm_chain.run({"query": query, "retrieved_contents": optimized_context})
    return response