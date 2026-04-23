from django.db import models


class Submission(models.Model):
    student_name = models.CharField("ФИО / группа", max_length=200, blank=True)
    answers = models.JSONField("Ответы (JSON)", default=dict)

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
        name = self.student_name or "без имени"
        return f"{name} — {self.score_auto_total}/15 авто ({self.created_at:%d.%m %H:%M})"
