from xml.sax.handler import property_encoding

from django.db import models
from django.contrib.auth.models import User
from markdownx.models import MarkdownxField
from markdownx.utils import markdown
import os

class Tag(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=200, unique=True, allow_unicode=True)
    def __str__(self):
        return self.name
    def get_absolute_url(self):
        return f'/blog/tag/{self.slug}/'

class Word_Tag(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=200, unique=True, allow_unicode=True)
    def __str__(self):
        return self.name
    def get_absolute_url(self):
        return f'/today_word/tag/{self.slug}/'

class Post(models.Model):
    title = models.CharField(max_length=30)
    content = MarkdownxField()

    head_image = models.ImageField(upload_to='blog/images/%Y/%m/%d/', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    tags = models.ManyToManyField(Tag, blank=True)

    view_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'[{self.pk}]{self.title} :: {self.author}'

    def get_absolute_url(self):
        return f'/blog/{self.pk}/'

    def get_file_name(self):
        return os.path.basename(self.file_upload.name)

    def get_file_ext(self):
        return self.get_file_name().split('.')[-1]

    def get_content_markdown(self):
        return markdown(self.content)

    @property
    def update_count(self):
        self.view_count += 1
        self.save()

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.author}::{self.content}'

    def get_absolute_url(self):
        return f'{self.post.get_absolute_url()}#comment-{self.pk}'


class Word(models.Model):
    title = models.CharField(max_length=30)
    content = MarkdownxField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    tags = models.ManyToManyField(Word_Tag, blank=True)

    def __str__(self):
        return f'[{self.pk}]{self.title} :: {self.author}'

    def get_absolute_url(self):
        return f'/today_word/{self.pk}/'

    def get_file_name(self):
        return os.path.basename(self.file_upload.name)

    def get_file_ext(self):
        return self.get_file_name().split('.')[-1]

    def get_content_markdown(self):
        return markdown(self.content)

class News(models.Model):
    title = models.CharField(max_length=30)
    content = MarkdownxField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    tags = models.ManyToManyField(Word_Tag, blank=True)

    def __str__(self):
        return f'[{self.pk}]{self.title} :: {self.author}'

    def get_absolute_url(self):
        return f'/news/{self.pk}/'

    def get_content_markdown(self):
        return markdown(self.content)


class Subject(models.Model):
    no = models.AutoField(primary_key=True, default=1)
    category = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    use_yn = models.BooleanField()


class RelatedWord(models.Model):
    no = models.IntegerField(primary_key=True)
    origin_num = models.IntegerField()
    origin_word = models.CharField(max_length=255)
    related_num = models.CharField(max_length=255, null=True)
    related_word = models.CharField(max_length=255)

