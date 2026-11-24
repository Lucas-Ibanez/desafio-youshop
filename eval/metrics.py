"""Métricas do Teste 1 (CONTEXTO 14.2): acurácia, kappa, precisão/recall, matriz, IC de Wilson."""

from __future__ import annotations

import math
import warnings
from collections.abc import Hashable, Sequence

from sklearn.metrics import cohen_kappa_score


def accuracy(y_true: Sequence[Hashable], y_pred: Sequence[Hashable]) -> float | None:
    if not y_true:
        return None
    return sum(t == p for t, p in zip(y_true, y_pred, strict=True)) / len(y_true)


def cohen_kappa(y_true: Sequence[Hashable], y_pred: Sequence[Hashable]) -> float | None:
    """Kappa de Cohen; None quando não está definido (ex.: uma classe só nos dois lados)."""
    if not y_true:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = cohen_kappa_score(list(y_true), list(y_pred))
    return None if math.isnan(value) else float(value)


def precision_recall(
    y_true: Sequence[Hashable], y_pred: Sequence[Hashable], positive: Hashable
) -> tuple[float | None, float | None]:
    tp = sum(t == positive and p == positive for t, p in zip(y_true, y_pred, strict=True))
    pred_pos = sum(p == positive for p in y_pred)
    true_pos = sum(t == positive for t in y_true)
    precision = tp / pred_pos if pred_pos else None
    recall = tp / true_pos if true_pos else None
    return precision, recall


def confusion(
    y_true: Sequence[Hashable], y_pred: Sequence[Hashable], labels: Sequence[Hashable]
) -> dict[Hashable, dict[Hashable, int]]:
    """matriz[gold][predito] = contagem."""
    matrix = {t: dict.fromkeys(labels, 0) for t in labels}
    for t, p in zip(y_true, y_pred, strict=True):
        matrix[t][p] += 1
    return matrix


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """Intervalo de Wilson (95% por padrão) para uma proporção."""
    if n == 0:
        return None
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, center - half), min(1.0, center + half)
