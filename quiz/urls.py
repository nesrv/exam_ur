from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing_view, name="quiz_landing"),
    path("start/", views.start_test_view, name="quiz_start"),
    path("test/", views.test_view, name="quiz_test"),
    path("test/progress/", views.save_progress_view, name="quiz_save_progress"),
    path("result/<int:pk>/", views.result_view, name="quiz_result"),
    path("stats/", views.stats_page, name="quiz_stats"),
    path("stats/api/", views.stats_api, name="quiz_stats_api"),
    path("stats/ping/", views.presence_ping, name="quiz_presence_ping"),
]
