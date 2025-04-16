from django.contrib import admin
from blog.models import Post, Tag, Comment


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'author',
        'published_at'
    ]
    list_filter = [
        'author',
        'tags',
        'published_at'
    ]
    raw_id_fields = ['author']
    search_fields = [
        'title',
        'text',
        'author__username'
    ]
    ordering = ['-published_at']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['title']
    search_fields = ['title']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = [
        'author',
        'post',
        'text',
        'published_at'
    ]
    list_select_related = ['author', 'post']
    raw_id_fields = ['author', 'post']
    search_fields = [
        'author__username',
        'text',
        'post__title'
    ]
    ordering = ['-published_at']
    list_filter = ['published_at']
