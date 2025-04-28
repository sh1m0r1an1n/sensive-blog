from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models import Count
from django.db.models import OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce


class PostQuerySet(models.QuerySet):
    def year(self, year):
        """Фильтрует посты по году публикации"""
        return self.filter(published_at__year=year)

    def with_likes_count(self):
        """Добавляет поле likes_count через подзапрос без тяжёлого GROUP BY."""
        through = Post.likes.through  # таблица связи M2M
        likes_subquery = (
            through.objects
            .filter(post_id=OuterRef("pk"))
            .values("post_id")
            .annotate(cnt=Count("id"))
            .values("cnt")[:1]
        )

        return self.annotate(
            likes_count=Coalesce(Subquery(likes_subquery, output_field=IntegerField()), 0)
        )

    def with_comments_count(self):
        """Добавляет поле comments_count через подзапрос."""
        comments_subquery = (
            Comment.objects
            .filter(post_id=OuterRef("pk"))
            .values("post_id")
            .annotate(cnt=Count("id"))
            .values("cnt")[:1]
        )

        return self.annotate(
            comments_count=Coalesce(Subquery(comments_subquery, output_field=IntegerField()), 0)
        )

    def with_related(self):
        """Оптимизированная загрузка связанных данных"""
        return self.select_related("author").prefetch_related("tags")

    def popular(self):
        """Возвращает посты, отсортированные по количеству лайков"""
        return self.with_likes_count().order_by("-likes_count")

    def bulk_load_comments_count(self):
        """Добавляет comments_count для всех постов в QuerySet"""
        posts_ids = [post.id for post in self]
        comments_counts = (
            Post.objects.with_comments_count()
            .filter(id__in=posts_ids)
            .values_list("id", "comments_count")
        )
        count_dict = dict(comments_counts)
        for post in self:
            post.comments_count = count_dict.get(post.id, 0)
        return self


class TagQuerySet(models.QuerySet):
    def popular(self):
        """Сортирует теги по количеству использующих их постов и добавляет количество под именем posts_with_tag для шаблонов."""
        return (
            self.annotate(posts_with_tag=Count("posts"))
            .order_by("-posts_with_tag")
        )


class Post(models.Model):
    title = models.CharField("Заголовок", max_length=200)
    text = models.TextField("Текст")
    slug = models.SlugField("Название в виде url", max_length=200)
    image = models.ImageField("Картинка")
    published_at = models.DateTimeField("Дата и время публикации", db_index=True)

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Автор",
        limit_choices_to={"is_staff": True},
    )
    likes = models.ManyToManyField(
        User, related_name="liked_posts", verbose_name="Кто лайкнул", blank=True
    )
    tags = models.ManyToManyField("Tag", related_name="posts", verbose_name="Теги")

    objects = PostQuerySet.as_manager()

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("post_detail", args={"slug": self.slug})

    class Meta:
        ordering = ["-published_at"]
        verbose_name = "пост"
        verbose_name_plural = "посты"


class Tag(models.Model):
    title = models.CharField("Тег", max_length=20, unique=True, db_index=True)

    objects = TagQuerySet.as_manager()

    def __str__(self):
        return self.title

    def clean(self):
        self.title = self.title.lower()

    class Meta:
        ordering = ["title"]
        verbose_name = "тег"
        verbose_name_plural = "теги"


class Comment(models.Model):
    post = models.ForeignKey(
        "Post",
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Пост, к которому написан",
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Автор")

    text = models.TextField("Текст комментария")
    published_at = models.DateTimeField("Дата и время публикации")

    def __str__(self):
        return f"{self.author.username} under {self.post.title}"

    class Meta:
        ordering = ["published_at"]
        verbose_name = "комментарий"
        verbose_name_plural = "комментарии"
