# python:3.10-bullseye 베이스 이미지 사용
FROM python:3.10-bullseye

WORKDIR /usr/src/app

# Python 환경 설정
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 필수 패키지 설치 및 SQLite 설치
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    wget \
    libsqlite3-dev \
    libomp5 \
    openjdk-11-jdk && \
    rm -rf /var/lib/apt/lists/* && \
    wget https://www.sqlite.org/2023/sqlite-autoconf-3420000.tar.gz && \
    tar xzf sqlite-autoconf-3420000.tar.gz && \
    cd sqlite-autoconf-3420000 && \
    ./configure && make && make install && \
    rm -rf sqlite-autoconf-3420000.tar.gz sqlite-autoconf-3420000

ENV LD_LIBRARY_PATH="/usr/local/lib:/usr/lib/x86_64-linux-gnu"
ENV JAVA_HOME="/usr/lib/jvm/java-11-openjdk-amd64"
ENV PATH="$JAVA_HOME/bin:$PATH"

# 다중 스레드 비활성화 설정 및 PyTorch CPU 강제 사용 설정
ENV OMP_NUM_THREADS=1
ENV CUDA_VISIBLE_DEVICES=""  
ENV PYTORCH_ENABLE_MPS_FALLBACK=0  
ENV TORCH_DEVICE="cpu"  

# 기존 디렉토리가 비어 있지 않다면 삭제
RUN rm -rf /usr/src/app/*

# Git 리포지토리 클론
RUN git clone https://github.com/yooobwoood/final_proj_blog.git /usr/src/app

WORKDIR /usr/src/app

# 환경 파일 복사
COPY .env /usr/src/app/.env
COPY .env.dev /usr/src/app/.env.dev
COPY .env.prod /usr/src/app/.env.prod
COPY .env.prod.db /usr/src/app/.env.prod.db

# Python 패키지 설치
RUN pip install --upgrade pip
RUN pip install django-crontab
RUN pip install -r requirements.txt

# faiss 설정 변경
RUN cd /usr/local/lib/python3.10/site-packages/faiss && \
    ln -s swigfaiss.py swigfaiss_avx2.py