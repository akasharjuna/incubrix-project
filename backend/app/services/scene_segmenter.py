"""
Scene segmentation: splits a script into meaningful scenes.
Groups sentences into scenes of roughly 10-20 seconds of narration,
preserving semantic continuity.
"""
from __future__ import annotations

import re
from typing import List, Tuple
from app.core.logging import get_logger

logger = get_logger(__name__)

# Approximate words per minute for a calm narration voice
WPM = 140
_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')


def _word_count(text: str) -> int:
    return len(text.split())


def _sentence_split(text: str) -> List[str]:
    """Split text into sentences, preserving meaning."""
    raw = _SENTENCE_RE.split(text.strip())
    sentences = [s.strip() for s in raw if s.strip()]
    return sentences


def _estimate_duration(text: str) -> float:
    """Estimate narration duration in seconds."""
    words = _word_count(text)
    return max(1.0, (words / WPM) * 60.0)


def segment_script(script: str, target_scene_duration: float = 12.0) -> List[dict]:
    """
    Divide a script into scenes.
    
    Returns a list of scene dicts with keys:
      scene_id, text, estimated_duration, estimated_start, estimated_end
    """
    sentences = _sentence_split(script)
    if not sentences:
        return []

    scenes = []
    current_sentences: List[str] = []
    current_duration = 0.0
    running_time = 0.0

    def flush(sents: List[str], start: float) -> dict:
        text = " ".join(sents)
        dur = _estimate_duration(text)
        return {
            "scene_id": f"scene-{len(scenes) + 1:03d}",
            "text": text,
            "estimated_duration": round(dur, 2),
            "estimated_start": round(start, 2),
            "estimated_end": round(start + dur, 2),
        }

    for sentence in sentences:
        sent_dur = _estimate_duration(sentence)
        if current_sentences and (current_duration + sent_dur) > target_scene_duration:
            scene = flush(current_sentences, running_time)
            running_time = scene["estimated_end"]
            scenes.append(scene)
            current_sentences = [sentence]
            current_duration = sent_dur
        else:
            current_sentences.append(sentence)
            current_duration += sent_dur

    if current_sentences:
        scene = flush(current_sentences, running_time)
        scenes.append(scene)

    logger.info("Segmented script into %d scenes", len(scenes))
    return scenes


def extract_visual_concepts(text: str) -> List[str]:
    """
    Extract key visual concepts from narration text.
    Returns multiple search query variants to improve footage retrieval.
    Handles disambiguation using simple contextual heuristics.
    """
    text_lower = text.lower()

    # Ambiguous word resolution using context
    ambiguous = {
        "bank": {
            "financial": ["financial bank building", "banking finance money"],
            "nature": ["river bank nature water"],
            "default": ["bank building"],
            "context": {
                "financial": ["money", "loan", "credit", "finance", "invest"],
                "nature": ["river", "water", "stream", "lake", "flood"],
            },
        },
        "cloud": {
            "computing": ["cloud computing server technology", "data center cloud"],
            "nature": ["clouds sky nature", "cumulus clouds blue sky"],
            "default": ["clouds sky"],
            "context": {
                "computing": ["server", "data", "computing", "aws", "azure", "storage", "digital"],
                "nature": ["weather", "rain", "storm", "sky", "sun"],
            },
        },
        "mouse": {
            "tech": ["computer mouse technology", "wireless mouse desk"],
            "animal": ["mouse animal rodent"],
            "default": ["mouse"],
            "context": {
                "tech": ["computer", "keyboard", "click", "desktop", "laptop"],
                "animal": ["trap", "cheese", "cat", "rodent", "wildlife"],
            },
        },
        "python": {
            "tech": ["python programming code", "software developer coding"],
            "animal": ["python snake reptile"],
            "default": ["python programming"],
            "context": {
                "tech": ["code", "programming", "script", "software", "developer", "data"],
                "animal": ["snake", "reptile", "wild", "jungle", "zoo"],
            },
        },
        "value": {
            "business": ["business value growth", "financial value chart"],
            "default": ["business value"],
            "context": {
                "business": ["company", "profit", "growth", "market", "stock"],
            },
        },
    }

    queries: List[str] = []

    for word, variants in ambiguous.items():
        if word in text_lower:
            resolved = variants["default"]
            for ctx_key, ctx_words in variants.get("context", {}).items():
                if any(cw in text_lower for cw in ctx_words):
                    resolved = variants[ctx_key]
                    break
            queries.extend(resolved)
            break  # Only resolve first ambiguous term found

    if not queries:
        # General extraction: take first 8 meaningful words (skip stopwords)
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "of", "in", "on", "at", "to", "for", "with", "by", "from",
            "it", "its", "this", "that", "these", "those", "and", "or",
            "but", "not", "so", "yet", "as", "if", "than", "then",
        }
        words = [
            w.lower().strip(".,!?;:\"'()")
            for w in text.split()
            if w.lower().strip(".,!?;:\"'()") not in stopwords
            and len(w) > 2
        ]
        primary = " ".join(words[:5])
        secondary = " ".join(words[:3])
        queries = [primary, secondary]

    # Deduplicate while preserving order
    seen: set = set()
    result: List[str] = []
    for q in queries:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            result.append(q)

    return result[:4]  # Max 4 queries per scene
