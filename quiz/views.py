from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .grading import grade_auto
from .models import Submission


def _collect_answers(post) -> dict:
    out: dict = {}
    for q in range(1, 6):
        key = str(q)
        val = post.get(f"q{q}")
        if val:
            out[key] = val.strip().upper()
    for q in range(6, 11):
        key = str(q)
        items = post.getlist(f"q{q}")
        out[key] = [x.strip().upper() for x in items if x.strip()]
    for q in range(11, 21):
        key = str(q)
        val = post.get(f"q{q}", "")
        out[key] = val.strip()
    return out


@require_http_methods(["GET", "POST"])
def test_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        answers = _collect_answers(request.POST)
        g = grade_auto(answers)
        sub = Submission.objects.create(
            student_name=request.POST.get("student_name", "").strip(),
            answers=answers,
            score_part1=g["score_part1"],
            score_part2=g["score_part2"],
            score_part3=g["score_part3"],
            score_auto_total=g["score_auto_total"],
            grading_detail={
                "part1": g["detail_part1"],
                "part2": g["detail_part2"],
                "part3": g["detail_part3"],
            },
        )
        request.session["last_submission_id"] = sub.id
        return redirect("quiz_result", pk=sub.pk)
    return render(request, "quiz/test.html")


def result_view(request: HttpRequest, pk: int) -> HttpResponse:
    sub = Submission.objects.filter(pk=pk).first()
    if not sub:
        return render(request, "quiz/result.html", {"error": "Сдача не найдена."}, status=404)
    if request.session.get("last_submission_id") != sub.id and not request.user.is_staff:
        return render(
            request,
            "quiz/result.html",
            {"error": "Результат доступен только после своей отправки."},
            status=403,
        )
    return render(request, "quiz/result.html", {"submission": sub})
