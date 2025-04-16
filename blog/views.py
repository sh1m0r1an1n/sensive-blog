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


def get_tags_with_posts_count():
    return Tag.objects.popular()


def get_posts_with_prefetched_data(queryset):
    return queryset.prefetch_related(
        "author", Prefetch("tags", queryset=Tag.objects.popular())
    ).with_likes_count()


def get_popular_posts():
    return get_posts_with_prefetched_data(Post.objects.all()).order_by("-likes_count")[
        :5
    ]


def get_all_posts():
    posts = get_posts_with_likes()
    posts = add_comments_count_to_posts(posts)

    return posts.prefetch_related(
        Prefetch("tags", queryset=get_tags_with_posts_count()),
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
        "comments_amount": getattr(post, "comments_count", 0),
        "likes_amount": getattr(post, "likes_count", 0),
        "image_url": post.image.url if post.image else None,
        "published_at": post.published_at,
        "slug": post.slug,
        "tags": [serialize_tag(tag) for tag in post.tags.all()],
        "first_tag_title": post.tags.all()[0].title if post.tags.all() else "",
    }


def serialize_tag(tag):
    return {
        "title": tag.title,
        "posts_with_tag": getattr(tag, "posts_count", 0),
    }


def index(request):
    popular_tags = get_tags_with_posts_count()[:5]
    most_popular_posts = get_popular_posts()

    posts_with_comments = (
        Post.objects.filter(id__in=[post.id for post in most_popular_posts])
        .annotate(comments_count=Count("comments"))
        .values_list("id", "comments_count")
    )
    comments_count_by_id = dict(posts_with_comments)

    fresh_posts = get_posts_with_prefetched_data(Post.objects.all()).order_by(
        "-published_at"
    )[:5]

    fresh_posts_with_comments = (
        Post.objects.filter(id__in=[post.id for post in fresh_posts])
        .annotate(comments_count=Count("comments"))
        .values_list("id", "comments_count")
    )
    fresh_comments_count_by_id = dict(fresh_posts_with_comments)

    for post in most_popular_posts:
        post.comments_count = comments_count_by_id.get(post.id, 0)

    for post in fresh_posts:
        post.comments_count = fresh_comments_count_by_id.get(post.id, 0)

    context = {
        "most_popular_posts": [serialize_post(post) for post in most_popular_posts],
        "page_posts": [serialize_post(post) for post in fresh_posts],
        "popular_tags": [serialize_tag(tag) for tag in popular_tags],
    }
    return render(request, "index.html", context)


def post_detail(request, slug):
    popular_tags = get_tags_with_posts_count()[:5]
    most_popular_posts = get_popular_posts()

    post = (
        Post.objects.prefetch_related(
            "author",
            Prefetch("tags", queryset=get_tags_with_posts_count()),
            Prefetch(
                "comments",
                queryset=Comment.objects.prefetch_related("author").order_by(
                    "published_at"
                ),
            ),
        )
        .with_likes_count()
        .get(slug=slug)
    )

    posts_with_comments = (
        Post.objects.filter(id__in=[post.id])
        .annotate(comments_count=Count("comments"))
        .values_list("id", "comments_count")
    )
    comments_count_by_id = dict(posts_with_comments)
    post.comments_count = comments_count_by_id.get(post.id, 0)

    serialized_comments = [
        {
            "text": comment.text,
            "published_at": comment.published_at,
            "author": comment.author.username,
        }
        for comment in post.comments.all()
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

    context = {
        "post": serialized_post,
        "popular_tags": [serialize_tag(tag) for tag in popular_tags],
        "most_popular_posts": [serialize_post(post) for post in most_popular_posts],
    }
    return render(request, "post-details.html", context)


def tag_filter(request, tag_title):
    tag = Tag.objects.get(title=tag_title)
    popular_tags = get_tags_with_posts_count()[:5]
    most_popular_posts = get_popular_posts()

    related_posts = get_posts_with_prefetched_data(
        Post.objects.filter(tags=tag)
    ).order_by("-published_at")[:20]

    posts_with_comments = (
        Post.objects.filter(id__in=[post.id for post in related_posts])
        .annotate(comments_count=Count("comments"))
        .values_list("id", "comments_count")
    )
    comments_count_by_id = dict(posts_with_comments)

    for post in related_posts:
        post.comments_count = comments_count_by_id.get(post.id, 0)

    context = {
        "tag": tag.title,
        "popular_tags": [serialize_tag(tag) for tag in popular_tags],
        "posts": [serialize_post(post) for post in related_posts],
        "most_popular_posts": [serialize_post(post) for post in most_popular_posts],
    }
    return render(request, "posts-list.html", context)


def contacts(request):
    # позже здесь будет код для статистики заходов на эту страницу
    # и для записи фидбека
    return render(request, "contacts.html", {})
