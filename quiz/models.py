from django.db import models


class Presence(models.Model):
    """Пульс браузера для публичной статистики «кто онлайн»."""

    client_id = models.CharField(max_length=48, unique=True, db_index=True)
    last_seen = models.DateTimeField(auto_now=True)
    variant = models.CharField(max_length=8, blank=True, default="")
    page = models.CharField(max_length=16, default="test")

    class Meta:
        verbose_name = "Присутствие"
        verbose_name_plural = "Присутствия"


class QuizProgress(models.Model):
    """Черновик ответов во время заполнения формы (живой прогресс для /stats/)."""

    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    display_name = models.CharField(max_length=200, blank=True)
    answers = models.JSONField(default=dict)
    clipboard_used = models.BooleanField("Было копирование на экране теста", default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Прогресс теста"
        verbose_name_plural = "Прогресс тестов"


class Submission(models.Model):
    variant = models.CharField(
        "Билет",
        max_length=8,
        default="v1",
        db_index=True,
        help_text="v1 / v2 / v3 — какой набор вопросов был на экране",
    )
    student_name = models.CharField("ФИО / группа", max_length=200, blank=True)
    answers = models.JSONField("Ответы (JSON)", default=dict)
    clipboard_used = models.BooleanField("Копирование на экране теста", default=False)

    score_part1 = models.PositiveSmallIntegerField(default=0)
    score_part2 = models.PositiveSmallIntegerField(default=0)
    score_part3 = models.PositiveSmallIntegerField(default=0)
    score_auto_total = models.PositiveSmallIntegerField(default=0)
    grading_detail = models.JSONField("Детали автопроверки", default=dict, blank=True)

    score_part4 = models.PositiveSmallIntegerField(
        "Баллы за часть 4 (вручную)", null=True, blank=True
    )
    teacher_comment = models.TextField("Комментарий преподавателя", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Сдача"
        verbose_name_plural = "Сдачи"

    def __str__(self) -> str:
        from quiz.variants import VARIANTS

        name = self.student_name or "без имени"
        lab = VARIANTS.get(self.variant, {}).get("label", self.variant)
        return f"{name} · {lab} — {self.score_auto_total}/15 авто ({self.created_at:%d.%m %H:%M})"
