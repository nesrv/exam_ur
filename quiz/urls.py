from django.urls import path

from . import views

urlpatterns = [
    path("", views.test_view, name="quiz_test"),
    path("result/<int:pk>/", views.result_view, name="quiz_result"),
]
