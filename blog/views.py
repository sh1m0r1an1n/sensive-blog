from django.shortcuts import render, get_object_or_404
from blog.models import Comment, Post, Tag
from django.db.models import Prefetch


def get_common_context():
    """Общие данные для всех шаблонов: популярные теги и посты."""
    popular_tags = Tag.objects.popular()[:5]

    popular_posts_qs = (
        get_posts_with_prefetched_data()
        .order_by("-likes_count")
    )[:5]

    popular_posts = [serialize_post(post) for post in popular_posts_qs]

    return {
        "popular_tags": popular_tags,
        "most_popular_posts": popular_posts,
    }


def get_tags_with_posts_count():
    return Tag.objects.popular()


def get_posts_with_prefetched_data():
    """Оптимизированный QuerySet для постов c выбранными полями, тегами, лайками и комментариями."""
    return (
        Post.objects
        .select_related("author")
        .prefetch_related(Prefetch("tags", queryset=Tag.objects.only("title")))
        .with_likes_count()
        .with_comments_count()
    )


def serialize_post(post: Post) -> dict:
    """Сериализация поста для шаблонов."""
    return {
        "title": post.title,
        "teaser_text": post.text[:200],
        "author": post.author.username,
        "comments_amount": getattr(post, "comments_count", 0),
        "likes_amount": getattr(post, "likes_count", 0),
        "image_url": post.image.url if post.image else None,
        "published_at": post.published_at,
        "slug": post.slug,
        "tags": list(post.tags.all()),
        "first_tag_title": post.tags.first().title if post.tags.exists() else None,
    }


def index(request):
    fresh_posts = get_posts_with_prefetched_data().order_by("-published_at")[:5]

    context = {
        **get_common_context(),
        "page_posts": [serialize_post(post) for post in fresh_posts],
    }
    return render(request, "index.html", context)


def post_detail(request, slug: str):
    post = get_object_or_404(
        Post.objects
        .select_related("author")
        .prefetch_related(
            "tags",
            Prefetch(
                "comments",
                queryset=Comment.objects.select_related("author"),
            ),
        )
        .with_likes_count()
        .with_comments_count(),
        slug=slug,
    )

    post_data = serialize_post(post)
    post_data["text"] = post.text
    post_data["comments"] = [
        {
            "author": comment.author.username,
            "text": comment.text,
            "published_at": comment.published_at,
        }
        for comment in post.comments.all()
    ]

    context = {
        **get_common_context(),
        "post": post_data,
    }
    return render(request, "post-details.html", context)


def tag_filter(request, tag_title: str):
    tag = get_object_or_404(Tag, title=tag_title)

    related_posts = (
        tag.posts
        .select_related("author")
        .prefetch_related(Prefetch("tags", queryset=Tag.objects.only("title")))
        .with_likes_count()
        .with_comments_count()
        .order_by("-published_at")[:20]
    )

    context = {
        **get_common_context(),
        "tag": tag.title,
        "posts": [serialize_post(post) for post in related_posts],
    }
    return render(request, "posts-list.html", context)


def contacts(request):
    return render(request, "contacts.html", {})