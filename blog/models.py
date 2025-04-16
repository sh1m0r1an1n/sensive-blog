from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models import Count


class PostQuerySet(models.QuerySet):
    def year(self, year):
        """Фильтрует посты по году публикации"""
        return self.filter(published_at__year=year)

    def popular(self):
        """
        Сортирует посты по популярности (количеству лайков)
        Возвращает QuerySet, поэтому можно объединять с другими методами
        """
        return self.annotate(likes_count=Count("likes")).order_by("-likes_count")

    def fetch_with_comments_count(self):
        """
        Добавляет количество комментариев к каждому посту используя один запрос к базе

        Этот метод лучше чем annotate(comments_count=Count('comments')) когда:
        1. Нужно посчитать комментарии для небольшого количества постов (например, после среза [:5])
        2. Уже применены фильтры/срезы и не нужно создавать сложный SQL JOIN

        Делает 2 простых запроса вместо 1 сложного:
        1. Получает все ID постов
        2. Считает комментарии только для этих постов

        Возвращает список постов вместо QuerySet, потому что мы добавляем
        атрибут comments_count напрямую к объектам постов
        """
        posts = self.all()
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


class TagQuerySet(models.QuerySet):
    def popular(self):
        """Сортирует теги по количеству использующих их постов"""
        return self.annotate(posts_count=Count("posts")).order_by("-posts_count")


class Post(models.Model):
    title = models.CharField("Заголовок", max_length=200)
    text = models.TextField("Текст")
    slug = models.SlugField("Название в виде url", max_length=200)
    image = models.ImageField("Картинка")
    published_at = models.DateTimeField("Дата и время публикации")

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
    title = models.CharField("Тег", max_length=20, unique=True)

    objects = TagQuerySet.as_manager()

    def __str__(self):
        return self.title

    def clean(self):
        self.title = self.title.lower()

    def get_absolute_url(self):
        return reverse("tag_filter", args={"tag_title": self.slug})

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
