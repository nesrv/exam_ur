from django.db import migrations, models


def forwards_bool_to_count(apps, schema_editor):
    QuizProgress = apps.get_model("quiz", "QuizProgress")
    Submission = apps.get_model("quiz", "Submission")
    for row in QuizProgress.objects.all():
        n = 1 if getattr(row, "clipboard_used", False) else 0
        row.clipboard_count = n
        row.save(update_fields=["clipboard_count"])
    for row in Submission.objects.all():
        n = 1 if getattr(row, "clipboard_used", False) else 0
        row.clipboard_count = n
        row.save(update_fields=["clipboard_count"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0005_clipboard_used"),
    ]

    operations = [
        migrations.AddField(
            model_name="quizprogress",
            name="clipboard_count",
            field=models.PositiveIntegerField(
                default=0, verbose_name="Число копирований на экране теста"
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="clipboard_count",
            field=models.PositiveIntegerField(
                default=0, verbose_name="Число копирований на экране теста"
            ),
        ),
        migrations.RunPython(forwards_bool_to_count, noop_reverse),
        migrations.RemoveField(model_name="quizprogress", name="clipboard_used"),
        migrations.RemoveField(model_name="submission", name="clipboard_used"),
    ]
