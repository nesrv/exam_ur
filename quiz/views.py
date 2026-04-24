import json
import random
import time
from datetime import timedelta

from django.db.utils import OperationalError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from .grading import grade_auto
from .models import Presence, QuizProgress, Submission
from .variants import VARIANT_IDS, VARIANTS

SESSION_QUIZ_VARIANT = "quiz_variant"
SESSION_QUIZ_ACTIVE = "quiz_test_active"
SESSION_PENDING_STUDENT = "quiz_pending_student"
PRESENCE_STALE = timedelta(minutes=15)
PROGRESS_LIVE = timedelta(seconds=90)
PROGRESS_MAX_AGE = timedelta(hours=6)
# Частые DELETE при каждом опросе /stats/api/ держат write-lock в SQLite.
_PRUNE_INTERVAL_SEC = 45.0
_last_prune_monotonic = 0.0


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


def _template_context(vid: str, prefilled_student_name: str) -> dict:
    v = VARIANTS[vid]
    return {
        "variant_label": v["label"],
        "heartbeat_variant": vid,
        "prefilled_student_name": prefilled_student_name,
        "part1": v["part1"],
        "part2": v["part2"],
        "part3": v["part3"],
        "part4": v["part4"],
    }


@require_http_methods(["GET"])
def landing_view(request: HttpRequest) -> HttpResponse:
    flash = request.session.pop("quiz_flash", None)
    return render(request, "quiz/landing.html", {"flash": flash})


@require_http_methods(["POST"])
def start_test_view(request: HttpRequest) -> HttpResponse:
    surname = (request.POST.get("surname") or "").strip()
    if len(surname) < 1:
        request.session["quiz_flash"] = "Введите фамилию."
        return redirect("quiz_landing")
    request.session[SESSION_PENDING_STUDENT] = surname
    request.session[SESSION_QUIZ_VARIANT] = random.choice(VARIANT_IDS)
    request.session[SESSION_QUIZ_ACTIVE] = True
    request.session.modified = True
    request.session.save()
    if request.session.session_key:
        QuizProgress.objects.filter(session_key=request.session.session_key).delete()
    return redirect("quiz_test")


@require_http_methods(["GET", "POST"])
def test_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        sk = request.session.session_key
        vid = request.session.get(SESSION_QUIZ_VARIANT)
        if not vid or vid not in VARIANTS or not request.session.get(SESSION_QUIZ_ACTIVE):
            request.session["quiz_flash"] = (
                "Сессия теста устарела. Начните с главной страницы."
            )
            return redirect("quiz_landing")
        answers = _collect_answers(request.POST)
        g = grade_auto(answers, vid)
        n_clip = 0
        if sk:
            qp = QuizProgress.objects.filter(session_key=sk).only("clipboard_count").first()
            if qp:
                n_clip = int(qp.clipboard_count)
        sub = Submission.objects.create(
            variant=vid,
            student_name=request.POST.get("student_name", "").strip(),
            answers=answers,
            clipboard_count=n_clip,
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
        if sk:
            QuizProgress.objects.filter(session_key=sk).delete()
        request.session["last_submission_id"] = sub.id
        request.session.pop(SESSION_QUIZ_VARIANT, None)
        request.session.pop(SESSION_QUIZ_ACTIVE, None)
        request.session.pop(SESSION_PENDING_STUDENT, None)
        return redirect("quiz_result", pk=sub.pk)

    if not request.session.get(SESSION_QUIZ_ACTIVE):
        request.session["quiz_flash"] = (
            "Сначала введите фамилию и нажмите «Начать тест»."
        )
        return redirect("quiz_landing")
    vid = request.session.get(SESSION_QUIZ_VARIANT)
    if not vid or vid not in VARIANTS:
        request.session["quiz_flash"] = "Сессия сброшена. Начните заново."
        request.session.pop(SESSION_QUIZ_ACTIVE, None)
        return redirect("quiz_landing")

    flash = request.session.pop("quiz_flash", None)
    prefilled = (request.session.get(SESSION_PENDING_STUDENT) or "").strip()
    ctx = _template_context(vid, prefilled)
    ctx["flash"] = flash
    return render(request, "quiz/test.html", ctx)


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


def _presence_upsert_with_retry(client_id: str, variant: str, page: str) -> bool:
    for attempt in range(4):
        try:
            Presence.objects.update_or_create(
                client_id=client_id,
                defaults={
                    "variant": variant,
                    "page": page,
                },
            )
            return True
        except OperationalError:
            time.sleep(0.03 * (2**attempt))
    return False


@require_GET
def presence_ping(request: HttpRequest) -> JsonResponse:
    cid = (request.GET.get("cid") or "").strip()[:48]
    if len(cid) < 8:
        return JsonResponse({"ok": False}, status=400)
    variant = (request.GET.get("v") or "").strip()[:8]
    if variant and variant not in VARIANT_IDS:
        variant = ""
    page = (request.GET.get("p") or "test").strip()[:16]
    if page not in ("test", "result", "stats", "landing"):
        page = "test"
    ok = _presence_upsert_with_retry(cid, variant, page)
    return JsonResponse({"ok": ok})


def _presence_prune() -> None:
    now = timezone.now()
    Presence.objects.filter(last_seen__lt=now - PRESENCE_STALE).delete()
    QuizProgress.objects.filter(updated_at__lt=now - PROGRESS_MAX_AGE).delete()


def _presence_prune_maybe() -> None:
    global _last_prune_monotonic
    now_m = time.monotonic()
    if now_m - _last_prune_monotonic < _PRUNE_INTERVAL_SEC:
        return
    try:
        _presence_prune()
    except OperationalError:
        # Повторить очистку раньше, чем через полный интервал
        _last_prune_monotonic = now_m - _PRUNE_INTERVAL_SEC + 10.0
    else:
        _last_prune_monotonic = now_m


def _session_key_for_storage(request: HttpRequest) -> str:
    if not request.session.session_key:
        request.session.create()
    key = request.session.session_key
    if not key:
        request.session.save()
        key = request.session.session_key or ""
    return key


def _normalize_draft_answers(raw) -> dict:
    """Принимает JSON с клиента: только ключи 1..20, безопасные типы."""
    if not isinstance(raw, dict):
        return {}
    out: dict = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not k.isdigit():
            continue
        n = int(k)
        if n < 1 or n > 20:
            continue
        key = str(n)
        if n <= 5:
            if isinstance(v, str):
                s = v.strip().upper()[:4]
                if s:
                    out[key] = s
        elif n <= 10:
            if isinstance(v, list):
                lst = [str(x).strip().upper()[:4] for x in v if str(x).strip()][:8]
                if lst:
                    out[key] = lst
            elif isinstance(v, str) and v.strip():
                out[key] = [v.strip().upper()[:4]]
        else:
            if isinstance(v, str) and v.strip():
                out[key] = v.strip()[:8000]
    return out


def _count_answered(answers: dict) -> int:
    """Сколько из 20 вопросов имеют непустой ответ в сохранённой сдаче."""
    n = 0
    for q in range(1, 21):
        key = str(q)
        v = answers.get(key)
        if q <= 5:
            if isinstance(v, str) and v.strip():
                n += 1
        elif q <= 10:
            if isinstance(v, list) and len(v) > 0:
                n += 1
        else:
            if isinstance(v, str) and v.strip():
                n += 1
    return n


def _submission_percent_base_100(sub: Submission) -> float:
    """Доля набранных баллов в % от максимума (15 или 20, если выставлена ч.4)."""
    auto = int(sub.score_auto_total)
    if sub.score_part4 is not None:
        return 100.0 * (auto + int(sub.score_part4)) / 20.0
    return 100.0 * auto / 15.0


def _mark_five_from_percent(pct: float) -> str:
    """Как в ТЗ: доля >80% → 5, >65% → 4, >50% → 3, иначе 2 (строго больше порога)."""
    if pct > 80:
        return "5"
    if pct > 65:
        return "4"
    if pct > 50:
        return "3"
    return "2"


def _stats_payload() -> dict:
    _presence_prune_maybe()
    now = timezone.now()
    fresh = now - PROGRESS_LIVE
    drafts = list(
        QuizProgress.objects.filter(updated_at__gte=fresh).order_by("-updated_at")[:2]
    )
    recent_subs = list(Submission.objects.order_by("-created_at")[:2])
    students: list[dict] = []
    di, si = 0, 0
    for _ in range(2):
        if di < len(drafts):
            d = drafts[di]
            di += 1
            filled = _count_answered(d.answers or {})
            students.append(
                {
                    "subtitle": (d.display_name or "").strip(),
                    "filled": filled,
                    "total": 20,
                    "result": "в процессе",
                    "grade": "—",
                    "live": True,
                    "clipboard_count": int(d.clipboard_count),
                    "copied": int(d.clipboard_count) > 0,
                    "mark_five": "—",
                    "scale_pct": None,
                }
            )
        elif si < len(recent_subs):
            sub = recent_subs[si]
            si += 1
            filled = _count_answered(sub.answers or {})
            pct = _submission_percent_base_100(sub)
            students.append(
                {
                    "subtitle": (sub.student_name or "").strip(),
                    "filled": filled,
                    "total": 20,
                    "result": f"{sub.score_auto_total}/15",
                    "grade": (
                        f"{sub.score_part4}/5"
                        if sub.score_part4 is not None
                        else "—"
                    ),
                    "live": False,
                    "clipboard_count": int(sub.clipboard_count),
                    "copied": int(sub.clipboard_count) > 0,
                    "mark_five": _mark_five_from_percent(pct),
                    "scale_pct": round(pct),
                }
            )
        else:
            students.append(
                {
                    "subtitle": "",
                    "filled": 0,
                    "total": 20,
                    "result": "—",
                    "grade": "—",
                    "live": False,
                    "clipboard_count": 0,
                    "copied": False,
                    "mark_five": "—",
                    "scale_pct": None,
                }
            )
    return {
        "server_time": timezone.localtime(now).isoformat(timespec="seconds"),
        "students": students,
    }


@require_http_methods(["POST"])
def save_progress_view(request: HttpRequest) -> JsonResponse:
    if not request.session.get(SESSION_QUIZ_ACTIVE):
        return JsonResponse({"ok": False, "error": "inactive"}, status=403)
    vid = request.session.get(SESSION_QUIZ_VARIANT)
    if not vid or vid not in VARIANTS:
        return JsonResponse({"ok": False, "error": "bad_variant"}, status=403)
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "json"}, status=400)
    answers = _normalize_draft_answers(body.get("answers"))
    pending = (request.session.get(SESSION_PENDING_STUDENT) or "").strip()
    dn = (body.get("display_name") or pending or "").strip()[:200]
    def _coerce_clipboard_count(raw) -> int:
        try:
            n = int(raw)
        except (TypeError, ValueError):
            n = 0
        return max(0, min(n, 9999))

    incoming_clip = _coerce_clipboard_count(body.get("clipboard_count"))
    sk = _session_key_for_storage(request)
    if not sk:
        return JsonResponse({"ok": False, "error": "session"}, status=500)
    prev_clip = (
        QuizProgress.objects.filter(session_key=sk)
        .values_list("clipboard_count", flat=True)
        .first()
    )
    if prev_clip is None:
        prev_clip = 0
    clip_final = max(int(prev_clip), incoming_clip)
    for attempt in range(4):
        try:
            QuizProgress.objects.update_or_create(
                session_key=sk,
                defaults={
                    "display_name": dn,
                    "answers": answers,
                    "clipboard_count": clip_final,
                },
            )
            break
        except OperationalError:
            if attempt == 3:
                return JsonResponse({"ok": False, "error": "locked"}, status=503)
            time.sleep(0.03 * (2**attempt))
    return JsonResponse({"ok": True, "filled": _count_answered(answers)})


@require_GET
def stats_api(request: HttpRequest) -> JsonResponse:
    return JsonResponse(_stats_payload())


@require_GET
def stats_page(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "quiz/stats.html",
        {"initial": _stats_payload()},
    )
