from django.apps import AppConfig
from django.db.backends.signals import connection_created


def _sqlite_pragmas(sender, connection, **kwargs) -> None:
    if connection.vendor != "sqlite":
        return
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")


class QuizConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "quiz"
    verbose_name = "Тестирование"

    def ready(self) -> None:
        connection_created.connect(
            _sqlite_pragmas, dispatch_uid="quiz_sqlite_wal_busy"
        )
