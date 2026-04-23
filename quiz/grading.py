"""Автопроверка частей 1–3 по ключу из for-test.md."""

from __future__ import annotations

PART1_KEY: dict[int, str] = {
    1: "C",
    2: "B",
    3: "B",
    4: "C",
    5: "C",
}

PART2_KEY: dict[int, frozenset[str]] = {
    6: frozenset({"B", "D"}),
    7: frozenset({"A", "C", "D"}),
    8: frozenset({"B", "D"}),
    9: frozenset({"A", "C", "D"}),
    10: frozenset({"A", "B", "D"}),
}

# Нормализованные допустимые ответы (после norm_answer) для части 3
PART3_ACCEPT: dict[int, frozenset[str]] = {
    11: frozenset({"оркестрация", "orchestration", "контейнернаяоркестрация"}),
    12: frozenset({"kanban", "канбан"}),
    13: frozenset({"gitops", "гитопс"}),
    14: frozenset(
        {
            "юниттестирование",
            "unitтестирование",
            "unittesting",
            "юниттесты",
            "unittest",
        }
    ),
    15: frozenset({"waterfall", "водопад", "водопаднаямодель", "каскаднаямодель"}),
}


def norm_answer(s: str) -> str:
    s = (s or "").strip().lower()
    for ch in (" ", "\t", "\n", "\r", "-", "_", "—", "–"):
        s = s.replace(ch, "")
    return s


def grade_part1(answers: dict) -> tuple[int, dict[int, bool]]:
    """answers: {"1": "C", ...}"""
    detail: dict[int, bool] = {}
    score = 0
    for q, correct in PART1_KEY.items():
        key = str(q)
        got = (answers.get(key) or "").strip().upper()
        ok = got == correct
        detail[q] = ok
        if ok:
            score += 1
    return score, detail


def grade_part2(answers: dict) -> tuple[int, dict[int, bool]]:
    """answers: {"6": ["B","D"], ...} или строки из формы."""
    detail: dict[int, bool] = {}
    score = 0
    for q, correct_set in PART2_KEY.items():
        key = str(q)
        raw = answers.get(key)
        if raw is None:
            got: frozenset[str] = frozenset()
        elif isinstance(raw, (list, tuple, set)):
            got = frozenset(str(x).strip().upper() for x in raw if str(x).strip())
        else:
            got = frozenset({str(raw).strip().upper()}) if str(raw).strip() else frozenset()
        ok = got == correct_set
        detail[q] = ok
        if ok:
            score += 1
    return score, detail


def grade_part3(answers: dict) -> tuple[int, dict[int, bool]]:
    detail: dict[int, bool] = {}
    score = 0
    for q, acceptable in PART3_ACCEPT.items():
        key = str(q)
        raw = answers.get(key)
        text = "" if raw is None else str(raw)
        n = norm_answer(text)
        ok = n in acceptable
        detail[q] = ok
        if ok:
            score += 1
    return score, detail


def grade_auto(answers: dict) -> dict:
    s1, d1 = grade_part1(answers)
    s2, d2 = grade_part2(answers)
    s3, d3 = grade_part3(answers)
    return {
        "score_part1": s1,
        "score_part2": s2,
        "score_part3": s3,
        "score_auto_total": s1 + s2 + s3,
        "detail_part1": {str(k): v for k, v in d1.items()},
        "detail_part2": {str(k): v for k, v in d2.items()},
        "detail_part3": {str(k): v for k, v in d3.items()},
    }
