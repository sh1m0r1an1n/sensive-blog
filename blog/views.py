from django.shortcuts import render
from blog.models import Comment, Post, Tag
from django.db.models import Count, Prefetch


def get_posts_with_likes():
    return Post.objects.annotate(likes_count=Count("likes"))


def get_comments_count_by_post_id(post_ids):
    comments_counts = (
        Post.objects.filter(id__in=post_ids)
        .annotate(comments_count=Count("comments"))
        .values_list("id", "comments_count")
    )
    return dict(comments_counts)


def add_comments_count_to_posts(posts):
    post_ids = [post.id for post in posts]
    comments_count_by_id = get_comments_count_by_post_id(post_ids)

    for post in posts:
        post.comments_count = comments_count_by_id.get(post.id, 0)

    return posts


def get_popular_tags():
    return Tag.objects.annotate(posts_count=Count("posts"))


def get_all_posts():
    posts = get_posts_with_likes()
    posts = add_comments_count_to_posts(posts)

    return posts.prefetch_related(
        Prefetch("tags", queryset=get_popular_tags()),
        "author",
    )


def get_posts_with_comments(posts_queryset):
    posts = posts_queryset.all()
    posts_ids = [post.id for post in posts]

    posts_with_comments = (
        Post.objects.filter(id__in=posts_ids)
        .annotate(comments_count=Count("comments"))
        .values_list("id", "comments_count")
    )
    count_for_id = dict(posts_with_comments)

    for post in posts:
        post.comments_count = count_for_id[post.id]

    return posts


def serialize_post(post):
    return {
        "title": post.title,
        "teaser_text": post.text[:200],
        "author": post.author.username,
        "comments_amount": post.comments_count,
        "image_url": post.image.url if post.image else None,
        "published_at": post.published_at,
        "slug": post.slug,
        "tags": [serialize_tag(tag) for tag in post.tags.all()],
        "first_tag_title": post.tags.all()[0].title,
    }


def serialize_tag(tag):
    return {
        "title": tag.title,
        "posts_with_tag": tag.posts.count(),
    }


def index(request):
    most_popular_posts = Post.objects.popular()[:5].fetch_with_comments_count()

    fresh_posts = Post.objects.all().order_by("-published_at")[:5]
    fresh_posts = fresh_posts.fetch_with_comments_count()

    most_popular_tags = Tag.objects.popular()[:5]

    context = {
        "most_popular_posts": [serialize_post(post) for post in most_popular_posts],
        "page_posts": [serialize_post(post) for post in fresh_posts],
        "popular_tags": [serialize_tag(tag) for tag in most_popular_tags],
    }
    return render(request, "index.html", context)


def post_detail(request, slug):
    post = Post.objects.get(slug=slug)
    post.comments_count = Comment.objects.filter(post=post).count()
    post.likes_count = post.likes.count()

    comments = Comment.objects.filter(post=post)
    serialized_comments = [
        {
            "text": comment.text,
            "published_at": comment.published_at,
            "author": comment.author.username,
        }
        for comment in comments
    ]

    serialized_post = {
        "title": post.title,
        "text": post.text,
        "author": post.author.username,
        "comments": serialized_comments,
        "likes_amount": post.likes_count,
        "image_url": post.image.url if post.image else None,
        "published_at": post.published_at,
        "slug": post.slug,
        "tags": [serialize_tag(tag) for tag in post.tags.all()],
    }

    most_popular_tags = Tag.objects.popular()[:5]
    most_popular_posts = Post.objects.popular()[:5].fetch_with_comments_count()

    context = {
        "post": serialized_post,
        "popular_tags": [serialize_tag(tag) for tag in most_popular_tags],
        "most_popular_posts": [serialize_post(post) for post in most_popular_posts],
    }
    return render(request, "post-details.html", context)


def tag_filter(request, tag_title):
    tag = Tag.objects.get(title=tag_title)

    related_posts = Post.objects.filter(tags=tag).popular()[:20]
    related_posts = related_posts.fetch_with_comments_count()

    most_popular_tags = Tag.objects.popular()[:5]
    most_popular_posts = Post.objects.popular()[:5].fetch_with_comments_count()

    context = {
        "tag": tag.title,
        "popular_tags": [serialize_tag(tag) for tag in most_popular_tags],
        "posts": [serialize_post(post) for post in related_posts],
        "most_popular_posts": [serialize_post(post) for post in most_popular_posts],
    }
    return render(request, "posts-list.html", context)


def contacts(request):
    # позже здесь будет код для статистики заходов на эту страницу
    # и для записи фидбека
    return render(request, "contacts.html", {})
