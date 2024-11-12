import pickle
import torch
import pandas as pd

from konlpy.tag import Okt
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
DATA_PATH = os.path.join(BASE_DIR, "data", "corpus-easystory.parquet")
FAISS_INDEX_PATH = os.path.join(BASE_DIR, "index", "easystory_faiss_index.pkl")
BM25_INDEX_PATH = os.path.join(BASE_DIR, "index", "easystory_bm25_index.pkl")
S3_FAISS_INDEX = "easystory_faiss_index.pkl"
S3_BM25_INDEX = "easystory_bm25_index.pkl"


# Load & Process Documents
def load_parquet_as_documents(file_path):
    df = pd.read_parquet(file_path, engine='pyarrow')
    documents = []
    for _, row in df.iterrows():
        content = row['contents']
        metadata = row['metadata']
        updated_metadata = {
            'doc_id': row['doc_id'],
            'next_id': metadata.get('next_id'),
            'prev_id': metadata.get('prev_id')
        }
        doc = Document(page_content=content, metadata=updated_metadata)
        documents.append(doc)
    return documents

# okt 한국어 형태소 분리기
okt = Okt()

def okt_tokenize(text):
    return okt.morphs(text)

# Create or Load Indexes
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
            model_name='intfloat/multilingual-e5-large-instruct',
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True},
        )
        faiss_index = FAISS.from_documents(documents, embedding_model).as_retriever(search_kwargs={"k": 30})
        with open(faiss_index_path, 'wb') as f:
            pickle.dump(faiss_index, f)
        
        bm25_index = BM25Retriever.from_documents(documents, preprocess_func=okt_tokenize)
        bm25_index.k = 30
        with open(bm25_index_path, 'wb') as f:
            pickle.dump(bm25_index, f)
    
    return faiss_index, bm25_index

# Hybrid Retriever CC method Setup
def create_hybrid_retriever(faiss_index, bm25_index):
    weights = [0.96, 0.04]
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
def rerank(query, retrieved_documents, tokenizer, model, top_k=5):
    pairs = [[query, doc.page_content] for doc in retrieved_documents]
    inputs = tokenizer(pairs, padding=True, truncation=True, return_tensors='pt', max_length=256) 
    with torch.no_grad():
        scores = model(**inputs, return_dict=True).logits.view(-1).float()
    reranked_docs = sorted(zip(retrieved_documents, scores), key=lambda x: x[1], reverse=True)
    return reranked_docs[:top_k]

# Optimize Context
def optimize_context(reranked_docs, max_tokens=8000):
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
        당신은 경제 금융 전문가 '정수빈'입니다.
        블로그 시리즈의 글을 작성한다고 생각해주세요.
        이 블로그는 경제 지식이 없거나 경제 개념을 쉽게 배우고 싶은 사람들을 대상으로 합니다.
        당신의 역할은 경제 용어에 대해 친절하고 쉽게 이해할 수 있는 설명을 제공하는 블로그 글을 작성하는 것입니다.

        블로그 글 초반부에서는 인사말을 반드시 작성해야 합니다. 
        '안녕하세요, 독자님들~ 수빈이입니다! 오늘도 저와 함께 쉽게 경제 공부를 해볼까요?' 등의 말로 시작해야 합니다.

        그 다음으로 개념을 상세하게 설명해 주세요. 
        그리고 쉬운 예시를 3개 만들어서 동화처럼 설명해 주세요.
        실생활에서 접할 수 있는 다양한 상황을 포함하도록 합니다.

        다음 단계로 이 용어를 이해하는 것이 왜 중요한지 요약해 주세요.

        글 마무리 문구도 작성해야 합니다.
        '오늘의 경제 공부는 어떠셨나요? 제 설명이 여러분께 도움이 되셨으면 좋겠어요. 오늘도 방문해주셔서 감사합니다 ^_^' 등의 말로 마무리해야 합니다.

        경제 지식이 전혀 없는 사람도 쉽게 이해하고 흥미롭게 읽을 수 있도록 친근하고 쉽게 작성해 주세요.

        # 주의사항:
        1. 문서의 내용을 기반으로만 글을 작성하세요. 내용을 지어내거나 사실과 다르게 작성하지 마세요.
        2. 문서에는 관련 메타데이터가 포함되어 있습니다. 메타데이터와 본문 내용을 모두 고려하여 정확한 답변을 제공하세요.
        3. 만약 설명할 수 없는 부분이 있다면, '모르겠습니다'라고 답하세요.
        4. 모든 제목은 #나 ## 같은 Markdown 표시 없이 굵은 글씨(**)로 나타나야 합니다. 예를 들어'## 경기가 무엇인가요?'는 '**경기가 무엇인가요?**'로 표시합니다.
        5. 본문과 인사말에서는 일반 텍스트 형식을 사용하고, 필요할 경우 단어에만 굵은 글씨를 사용해주세요.
        6. 글은 최대한 길게 작성해 주세요.
        7. 글 초반부 인사와 마무리 인사는 길고 다채롭게 표현하면 좋습니다.
        8. 글 초반부 인사 : 약 500자, 마무리 인사 : 약 500자 길이로 작성해 주세요.

        이제 주제에 맞게 블로그 글을 작성해 주세요.
        질문: {query}
        단락: {retrieved_contents}
        답변:
        """
    )
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    return LLMChain(llm=llm, prompt=prompt_template)

# Initialize RAG System
def initialize_rag_system():
    documents = load_parquet_as_documents(DATA_PATH)
    faiss_index, bm25_index = load_or_create_index(documents, FAISS_INDEX_PATH, BM25_INDEX_PATH)
    hybrid_retriever = create_hybrid_retriever(faiss_index, bm25_index)
    tokenizer, model = initialize_reranker()
    llm_chain = initialize_llm_chain()
    return hybrid_retriever, tokenizer, model, llm_chain

# Main Query Processing Function (Retrieve and Rerank)
def generate_answer(query, hybrid_retriever, tokenizer, model, top_k_retrieve=30, top_k_rerank=5):
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

