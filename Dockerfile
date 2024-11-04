FROM python:3.10-slim-buster

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1 

RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && wget https://www.sqlite.org/2023/sqlite-autoconf-3420000.tar.gz \
    && tar xzf sqlite-autoconf-3420000.tar.gz \
    && cd sqlite-autoconf-3420000 \
    && ./configure && make && make install \
    && rm -rf sqlite-autoconf-3420000.tar.gz sqlite-autoconf-3420000

ENV LD_LIBRARY_PATH="/usr/local/lib"

COPY . /usr/src/app/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt 