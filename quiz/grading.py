"""Автопроверка частей 1–3 по ключам выбранного билета (v1 / v2 / v3)."""

from __future__ import annotations

from .variants import VARIANTS


def norm_answer(s: str) -> str:
    s = (s or "").strip().lower()
    for ch in (" ", "\t", "\n", "\r", "-", "_", "—", "–"):
        s = s.replace(ch, "")
    return s


def grade_part1(
    answers: dict, part1_key: dict[int, str]
) -> tuple[int, dict[int, bool]]:
    detail: dict[int, bool] = {}
    score = 0
    for q, correct in part1_key.items():
        key = str(q)
        got = (answers.get(key) or "").strip().upper()
        ok = got == correct
        detail[q] = ok
        if ok:
            score += 1
    return score, detail


def grade_part2(
    answers: dict, part2_key: dict[int, frozenset[str]]
) -> tuple[int, dict[int, bool]]:
    detail: dict[int, bool] = {}
    score = 0
    for q, correct_set in part2_key.items():
        key = str(q)
        raw = answers.get(key)
        if raw is None:
            got: frozenset[str] = frozenset()
        elif isinstance(raw, (list, tuple, set)):
            got = frozenset(str(x).strip().upper() for x in raw if str(x).strip())
        else:
            got = (
                frozenset({str(raw).strip().upper()}) if str(raw).strip() else frozenset()
            )
        ok = got == correct_set
        detail[q] = ok
        if ok:
            score += 1
    return score, detail


def grade_part3(
    answers: dict, part3_accept: dict[int, frozenset[str]]
) -> tuple[int, dict[int, bool]]:
    detail: dict[int, bool] = {}
    score = 0
    for q, acceptable in part3_accept.items():
        key = str(q)
        raw = answers.get(key)
        text = "" if raw is None else str(raw)
        n = norm_answer(text)
        ok = n in acceptable
        detail[q] = ok
        if ok:
            score += 1
    return score, detail


def grade_auto(answers: dict, variant_id: str) -> dict:
    spec = VARIANTS[variant_id]["keys"]
    s1, d1 = grade_part1(answers, spec["part1"])
    s2, d2 = grade_part2(answers, spec["part2"])
    s3, d3 = grade_part3(answers, spec["part3"])
    return {
        "score_part1": s1,
        "score_part2": s2,
        "score_part3": s3,
        "score_auto_total": s1 + s2 + s3,
        "detail_part1": {str(k): v for k, v in d1.items()},
        "detail_part2": {str(k): v for k, v in d2.items()},
        "detail_part3": {str(k): v for k, v in d3.items()},
    }
