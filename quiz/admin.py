from html import escape

from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "student_name",
        "score_auto_total",
        "score_part4",
        "created_at",
    )
    list_editable = ("score_part4",)
    list_filter = ("created_at",)
    search_fields = ("student_name",)
    readonly_fields = (
        "part4_display",
        "answers",
        "score_part1",
        "score_part2",
        "score_part3",
        "score_auto_total",
        "grading_detail",
        "created_at",
    )

    @admin.display(description="Часть 4 (ответы студента)")
    def part4_display(self, obj: Submission) -> str:
        if not obj or not obj.pk:
            return "—"
        blocks = []
        for i in range(16, 21):
            text = obj.answers.get(str(i), "") or ""
            blocks.append(
                f"<p><strong>Вопрос {i}</strong></p>"
                f"<pre style='margin:0 0 1rem;white-space:pre-wrap;font:inherit'>{escape(text)}</pre>"
            )
        return mark_safe("".join(blocks))

    fieldsets = (
        (None, {"fields": ("student_name", "created_at")}),
        (
            "Автопроверка (части 1–3)",
            {
                "fields": (
                    "score_part1",
                    "score_part2",
                    "score_part3",
                    "score_auto_total",
                    "grading_detail",
                )
            },
        ),
        (
            "Часть 4 — вручную",
            {"fields": ("part4_display", "score_part4", "teacher_comment")},
        ),
        ("Все ответы (JSON)", {"fields": ("answers",), "classes": ("collapse",)}),
    )
