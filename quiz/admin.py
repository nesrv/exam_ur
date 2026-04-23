from html import escape

from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import QuizProgress, Submission
from .variants import VARIANTS


@admin.register(QuizProgress)
class QuizProgressAdmin(admin.ModelAdmin):
    list_display = ("display_name", "clipboard_used", "session_key", "updated_at")
    readonly_fields = ("session_key", "display_name", "answers", "clipboard_used", "updated_at")
    search_fields = ("display_name", "session_key")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "student_name",
        "variant_display",
        "score_auto_total",
        "clipboard_used",
        "score_part4",
        "created_at",
    )
    list_editable = ("score_part4",)
    list_filter = ("created_at", "variant")
    search_fields = ("student_name",)
    readonly_fields = (
        "variant_display",
        "part4_display",
        "answers",
        "clipboard_used",
        "score_part1",
        "score_part2",
        "score_part3",
        "score_auto_total",
        "grading_detail",
        "created_at",
    )

    @admin.display(description="Вариант")
    def variant_display(self, obj: Submission) -> str:
        if not obj or not obj.pk:
            return "—"
        lab = VARIANTS.get(obj.variant, {}).get("label", "")
        return f"{lab} ({obj.variant})" if lab else obj.variant

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
        (None, {"fields": ("student_name", "variant_display", "created_at")}),
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
