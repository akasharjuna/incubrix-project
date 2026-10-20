"""
Semantic B-roll matching engine.

Computes a composite relevance score for each candidate clip:
  score = w_sem * semantic_sim
        + w_hint * hint_sim
        + w_dur * duration_score
        + w_ar * aspect_ratio_score

Scores are normalized to [0, 1]. They represent model-estimated relevance,
not proven probabilities of being the "best" clip.
"""
from __future__ import annotations

import functools
from typing import List, Optional, Tuple

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.job import ClipInfo

logger = get_logger(__name__)

_model = None  # Lazy-loaded sentence transformer


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            settings = get_settings()
            logger.info("Loading embedding model: %s", settings.embedding_model)
            _model = SentenceTransformer(settings.embedding_model)
            logger.info("Embedding model loaded.")
        except ImportError:
            logger.warning("sentence-transformers not installed; using TF-IDF fallback.")
            _model = "tfidf"
    return _model


def _cosine_similarity(a, b) -> float:
    """Compute cosine similarity between two vectors."""
    import numpy as np
    a, b = np.array(a), np.array(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _tfidf_similarity(text_a: str, text_b: str) -> float:
    """Simple word-overlap fallback similarity."""
    a_words = set(text_a.lower().split())
    b_words = set(text_b.lower().split())
    if not a_words or not b_words:
        return 0.0
    return len(a_words & b_words) / len(a_words | b_words)


def semantic_similarity(text_a: str, text_b: str) -> float:
    """
    Compute semantic similarity between two text strings.
    Returns a float in [0, 1].
    Note: this is a model-estimated score, not a proven probability.
    """
    model = _get_model()
    if model == "tfidf":
        return _tfidf_similarity(text_a, text_b)
    try:
        embs = model.encode([text_a, text_b], normalize_embeddings=True)
        sim = _cosine_similarity(embs[0], embs[1])
        # Clamp to [0, 1]
        return max(0.0, min(1.0, float(sim)))
    except Exception as exc:
        logger.warning("Embedding failed, falling back to TF-IDF: %s", exc)
        return _tfidf_similarity(text_a, text_b)


def _duration_score(clip_duration: float, target_duration: float) -> float:
    """Score how well a clip's duration matches the target scene duration."""
    if clip_duration <= 0 or target_duration <= 0:
        return 0.0
    ratio = clip_duration / target_duration
    if ratio >= 1.0:
        # Clip is long enough — good
        return min(1.0, 1.0 - (ratio - 1.0) * 0.1)
    else:
        # Clip is too short — penalise
        return ratio * 0.8


def _aspect_ratio_score(clip_width: int, clip_height: int, target_ar: str) -> float:
    """Score clip's natural aspect ratio against the requested output ratio."""
    if clip_width <= 0 or clip_height <= 0:
        return 0.5
    clip_ar = clip_width / clip_height
    target_ratios = {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1.0}
    target = target_ratios.get(target_ar, 16 / 9)
    diff = abs(clip_ar - target) / target
    return max(0.0, 1.0 - diff)


def score_clip(
    scene_text: str,
    clip_title: str,
    visual_hint: Optional[str],
    clip: ClipInfo,
    target_duration: float,
    target_ar: str = "16:9",
) -> Tuple[float, str]:
    """
    Compute composite relevance score for a single clip.

    Returns (score, explanation_string).
    """
    settings = get_settings()

    # Semantic similarity between scene narration and clip title/description
    sem_sim = semantic_similarity(scene_text, clip_title)

    # Visual hint alignment
    if visual_hint:
        hint_sim = semantic_similarity(visual_hint, clip_title)
    else:
        hint_sim = sem_sim  # No hint → use semantic score

    dur_score = _duration_score(clip.duration, target_duration)
    ar_score = _aspect_ratio_score(clip.width, clip.height, target_ar)

    # Weighted composite
    score = (
        settings.semantic_weight * sem_sim
        + settings.visual_hint_weight * hint_sim
        + settings.duration_weight * dur_score
        + settings.aspect_ratio_weight * ar_score
    )
    score = max(0.0, min(1.0, score))

    reason = (
        f"Semantic similarity={sem_sim:.2f}, "
        f"hint_alignment={hint_sim:.2f}, "
        f"duration_fit={dur_score:.2f}, "
        f"aspect_ratio_fit={ar_score:.2f} → "
        f"composite={score:.2f}"
    )
    return round(score, 4), reason


def rank_clips(
    scene_text: str,
    visual_hint: Optional[str],
    candidates: List[Tuple[str, ClipInfo]],  # (title, clip)
    target_duration: float,
    target_ar: str = "16:9",
    used_asset_ids: Optional[set] = None,
) -> List[Tuple[float, str, ClipInfo]]:
    """
    Rank a list of candidate clips for a scene.
    Returns sorted list of (score, reason, clip) — highest score first.
    Penalises already-used clips to avoid duplicate usage.
    """
    used_asset_ids = used_asset_ids or set()
    ranked = []

    for title, clip in candidates:
        score, reason = score_clip(
            scene_text, title, visual_hint, clip, target_duration, target_ar
        )
        # Penalise reuse
        if clip.asset_id in used_asset_ids:
            score = score * 0.5
            reason = f"[REUSE PENALISED] {reason}"
        ranked.append((score, reason, clip))

    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked
