from django.contrib import admin
from markdownx.admin import MarkdownxModelAdmin
from .models import Post, Tag, Comment, Word, Word_Tag, News

admin.site.register(Post, MarkdownxModelAdmin)
admin.site.register(Word, MarkdownxModelAdmin)
admin.site.register(News, MarkdownxModelAdmin)

admin.site.register(Comment)

class TagAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name', )}

# admin.site.register(Category, CategoryAdmin)
admin.site.register(Tag, TagAdmin)
# admin.site.register(Word_Category, CategoryAdmin)
admin.site.register(Word_Tag, TagAdmin)


