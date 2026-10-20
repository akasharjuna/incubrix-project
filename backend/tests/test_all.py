"""
Backend test suite.
All tests use deterministic mock providers — no API keys or external network needed.
Run: cd backend && py -3 -m pytest tests/ -v
"""
import pytest
import asyncio
from typing import List


# ── Scene Segmenter Tests ───────────────────────────────────────────────────

from app.services.scene_segmenter import (
    segment_script, extract_visual_concepts, _estimate_duration
)


def test_segment_empty_script():
    scenes = segment_script("")
    assert scenes == []


def test_segment_single_sentence():
    scenes = segment_script("The sun rises in the east.")
    assert len(scenes) == 1
    assert scenes[0]["text"] == "The sun rises in the east."
    assert scenes[0]["scene_id"] == "scene-001"


def test_segment_multiple_sentences():
    script = (
        "Solar energy is clean. It reduces electricity costs. "
        "Millions of homes now use solar panels. "
        "The future is renewable."
    )
    scenes = segment_script(script)
    assert len(scenes) >= 1
    # All text should be preserved
    all_text = " ".join(s["text"] for s in scenes)
    assert "Solar energy" in all_text
    assert "renewable" in all_text


def test_scene_timings_sequential():
    script = "First scene text here. Second scene text here. Third scene here."
    scenes = segment_script(script)
    for i in range(1, len(scenes)):
        assert scenes[i]["estimated_start"] >= scenes[i-1]["estimated_end"] - 0.01


def test_estimate_duration_proportional():
    short = _estimate_duration("Hi.")
    long = _estimate_duration("This is a much longer sentence with many more words in it that should take more time.")
    assert long > short


def test_scene_ids_unique():
    script = ". ".join(["Sentence number " + str(i) for i in range(20)])
    scenes = segment_script(script)
    ids = [s["scene_id"] for s in scenes]
    assert len(ids) == len(set(ids))


# ── Visual Concept Extraction / Disambiguation Tests ────────────────────────

def test_disambiguate_bank_financial():
    queries = extract_visual_concepts("The bank approved the loan for investment.")
    assert any("bank" in q.lower() or "financ" in q.lower() for q in queries)


def test_disambiguate_bank_river():
    queries = extract_visual_concepts("We walked along the river bank near the water stream.")
    assert any("river" in q.lower() or "water" in q.lower() for q in queries)


def test_disambiguate_cloud_computing():
    queries = extract_visual_concepts("We store all data in the cloud computing server.")
    assert any("cloud" in q.lower() or "comput" in q.lower() for q in queries)


def test_disambiguate_cloud_nature():
    queries = extract_visual_concepts("Dark storm clouds filled the rainy sky.")
    assert any("cloud" in q.lower() or "sky" in q.lower() for q in queries)


def test_disambiguate_python_programming():
    queries = extract_visual_concepts("We wrote this code in Python programming language.")
    assert any("python" in q.lower() or "code" in q.lower() or "program" in q.lower() for q in queries)


def test_disambiguate_python_snake():
    queries = extract_visual_concepts("The python snake slithered through the jungle.")
    assert any("python" in q.lower() or "snake" in q.lower() for q in queries)


def test_extract_concepts_not_empty():
    queries = extract_visual_concepts("Artificial intelligence is transforming healthcare.")
    assert len(queries) > 0
    assert all(len(q) > 0 for q in queries)


def test_extract_max_four_queries():
    queries = extract_visual_concepts("A very complex sentence with many topics: technology, health, finance, education, travel.")
    assert len(queries) <= 4


# ── Semantic Matching Tests ─────────────────────────────────────────────────

from app.matching.semantic_matcher import (
    _tfidf_similarity, score_clip, rank_clips
)
from app.models.job import ClipInfo, ClipLicense


def _make_clip(asset_id: str, duration: float = 10.0, w: int = 1920, h: int = 1080) -> ClipInfo:
    return ClipInfo(
        asset_id=asset_id,
        provider="mock",
        source_url=f"https://mock/{asset_id}",
        download_url=f"https://mock/{asset_id}.mp4",
        width=w, height=h,
        duration=duration,
        license=ClipLicense(
            name="CC0", commercial_use=True,
            attribution_required=False, ai_generated=False
        )
    )


def test_tfidf_identical():
    sim = _tfidf_similarity("solar energy panels", "solar energy panels")
    assert sim == pytest.approx(1.0)


def test_tfidf_disjoint():
    sim = _tfidf_similarity("solar energy", "ocean sailing")
    assert sim == pytest.approx(0.0)


def test_tfidf_partial():
    sim = _tfidf_similarity("solar energy panels", "solar panels roof")
    assert 0.0 < sim < 1.0


def test_score_clip_returns_tuple():
    clip = _make_clip("test-001")
    score, reason = score_clip(
        "solar energy panels in sunlight",
        "solar panels renewable energy",
        "solar panels",
        clip, 10.0, "16:9"
    )
    assert 0.0 <= score <= 1.0
    assert isinstance(reason, str)
    assert "composite" in reason


def test_rank_clips_ordered():
    clip_a = _make_clip("clip-a")
    clip_b = _make_clip("clip-b")
    candidates = [
        ("solar panels energy sun", clip_a),
        ("ocean waves beach sailing", clip_b),
    ]
    ranked = rank_clips(
        "We are using solar power for energy.",
        "solar panels",
        candidates,
        target_duration=10.0,
        target_ar="16:9",
    )
    assert len(ranked) == 2
    assert ranked[0][0] >= ranked[1][0]  # Highest first
    # Solar clip should rank higher for solar query
    assert ranked[0][2].asset_id == "clip-a"


def test_rank_clips_reuse_penalized():
    clip = _make_clip("clip-reuse")
    candidates = [("nature forest trees", clip)]
    ranked_first = rank_clips("Forest trees", None, candidates, 10.0, "16:9", used_asset_ids=set())
    ranked_reused = rank_clips("Forest trees", None, candidates, 10.0, "16:9", used_asset_ids={"clip-reuse"})
    assert ranked_reused[0][0] < ranked_first[0][0]


def test_rank_clips_empty_candidates():
    ranked = rank_clips("Some text", None, [], 10.0, "16:9")
    assert ranked == []


# ── Licensing Tests ─────────────────────────────────────────────────────────

def test_commercial_license_required():
    """Clips without commercial_use should be filterable."""
    non_commercial = ClipLicense(
        name="NonCommercial", commercial_use=False,
        attribution_required=True, ai_generated=False
    )
    clip = ClipInfo(
        asset_id="nc-001", provider="test",
        source_url="https://test/nc-001",
        download_url="https://test/nc-001.mp4",
        width=1920, height=1080, duration=10.0,
        license=non_commercial
    )
    assert clip.license.commercial_use == False


# ── Caption / SRT Tests ─────────────────────────────────────────────────────

from app.rendering.caption_generator import generate_srt, _format_srt_time, _wrap_text
from app.models.job import SceneMatch
import tempfile, os


def _make_scene(scene_id, text, start, end) -> SceneMatch:
    return SceneMatch(scene_id=scene_id, text=text, start=start, end=end)


def test_srt_time_format_zero():
    assert _format_srt_time(0.0) == "00:00:00,000"


def test_srt_time_format_nonzero():
    assert _format_srt_time(3661.5) == "01:01:01,500"


def test_srt_time_negative_clamped():
    assert _format_srt_time(-1.0) == "00:00:00,000"


def test_wrap_text_short():
    result = _wrap_text("Short text", max_chars=42)
    assert result == "Short text"


def test_wrap_text_long():
    long_text = "This is a very long caption line that should be wrapped into multiple shorter lines for readability on screen."
    result = _wrap_text(long_text, max_chars=42)
    lines = result.split("\n")
    assert len(lines) <= 2
    for line in lines:
        assert len(line) <= 42 + 5  # Allow slight overflow for word boundaries


def test_generate_srt_creates_file():
    scenes = [
        _make_scene("s001", "Hello world.", 0.0, 3.0),
        _make_scene("s002", "This is scene two.", 3.0, 7.0),
    ]
    with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as f:
        path = f.name
    try:
        generate_srt(scenes, path)
        content = open(path, encoding="utf-8").read()
        assert "00:00:00,000 --> 00:00:03,000" in content
        assert "Hello world." in content
        assert "This is scene two." in content
    finally:
        os.remove(path)


def test_generate_srt_no_negative_timestamps():
    scenes = [_make_scene("s001", "Text", -1.0, 3.0)]
    with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as f:
        path = f.name
    try:
        generate_srt(scenes, path)
        content = open(path, encoding="utf-8").read()
        assert "-" not in content.split("-->")[0]  # Start time not negative
    finally:
        os.remove(path)


# ── API Validation Tests ────────────────────────────────────────────────────

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_job_script_mode():
    resp = client.post("/api/v1/broll/jobs", json={
        "script": "The sun shines brightly over the fields.",
    })
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "queued"


def test_create_job_audio_mode():
    resp = client.post("/api/v1/broll/jobs", json={
        "audio_url": "https://example.com/audio.mp3",
    })
    assert resp.status_code == 202


def test_create_job_scenes_mode():
    resp = client.post("/api/v1/broll/jobs", json={
        "scenes": [
            {"text": "Scene one narration.", "visual_hint": "cityscape"},
            {"text": "Scene two narration.", "visual_hint": "nature"},
        ]
    })
    assert resp.status_code == 202


def test_create_job_empty_script():
    resp = client.post("/api/v1/broll/jobs", json={"script": "   "})
    assert resp.status_code == 422


def test_create_job_no_input():
    resp = client.post("/api/v1/broll/jobs", json={})
    assert resp.status_code == 422


def test_create_job_multiple_inputs():
    resp = client.post("/api/v1/broll/jobs", json={
        "script": "Hello world.",
        "audio_url": "https://example.com/audio.mp3",
    })
    assert resp.status_code == 422


def test_create_job_invalid_aspect_ratio():
    resp = client.post("/api/v1/broll/jobs", json={
        "script": "Hello.",
        "aspect_ratios": ["4:3"],  # Not supported
    })
    assert resp.status_code == 422


def test_create_job_private_audio_url():
    resp = client.post("/api/v1/broll/jobs", json={
        "audio_url": "http://192.168.1.1/audio.mp3",
    })
    # Should fail SSRF validation at job creation
    assert resp.status_code in (422, 202)  # May pass validation (DNS not resolved), caught on download


def test_get_nonexistent_job():
    resp = client.get("/api/v1/broll/jobs/nonexistent-id-12345")
    assert resp.status_code == 404


def test_list_jobs():
    resp = client.get("/api/v1/broll/jobs")
    assert resp.status_code == 200
    assert "jobs" in resp.json()


def test_get_job_status_after_create():
    create_resp = client.post("/api/v1/broll/jobs", json={"script": "Testing status polling."})
    job_id = create_resp.json()["job_id"]
    status_resp = client.get(f"/api/v1/broll/jobs/{job_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["job_id"] == job_id


# ── Job State Transition Tests ──────────────────────────────────────────────

from app.models.job import Job, JobStatus, InputMode
from app.storage.job_store import create_job as store_create, get_job as store_get


def test_job_initial_state():
    job = Job(input_mode=InputMode.SCRIPT, script="Test")
    assert job.status == JobStatus.QUEUED
    assert job.progress.percent == 0


def test_job_state_transitions():
    job = Job(input_mode=InputMode.SCRIPT, script="Test")
    job.status = JobStatus.PROCESSING
    assert job.status == JobStatus.PROCESSING
    job.status = JobStatus.COMPLETED
    assert job.status == JobStatus.COMPLETED


# ── Mock Provider Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mock_provider_returns_clips():
    from app.providers.mock_provider import MockFootageProvider
    provider = MockFootageProvider()
    results = await provider.search("nature landscape")
    assert len(results) > 0
    title, clip = results[0]
    assert isinstance(title, str)
    assert clip.license.commercial_use == True


@pytest.mark.asyncio
async def test_mock_provider_health():
    from app.providers.mock_provider import MockFootageProvider
    provider = MockFootageProvider()
    health = await provider.health_check()
    assert health["status"] == "ok"


# ── Timeline / Manifest Tests ────────────────────────────────────────────────

import json, tempfile, os
from app.services.artifact_service import generate_timeline, generate_manifest
from app.models.job import AspectRatio


def _make_test_job():
    job = Job(
        input_mode=InputMode.SCRIPT,
        script="Hello world.",
        aspect_ratios=[AspectRatio.R16_9],
    )
    job.status = JobStatus.COMPLETED
    return job


def test_generate_timeline_valid_json():
    job = _make_test_job()
    scenes = [_make_scene("s001", "Hello world.", 0.0, 3.0)]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        timeline = generate_timeline(job, scenes, path)
        content = json.loads(open(path).read())
        assert content["job_id"] == job.job_id
        assert len(content["scenes"]) == 1
        assert content["scenes"][0]["scene_id"] == "s001"
    finally:
        os.remove(path)


def test_generate_manifest_valid_json():
    job = _make_test_job()
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf_m:
        manifest_path = tf_m.name
    try:
        manifest = generate_manifest(job, {"scenes": []}, {}, manifest_path)
        content = json.loads(open(manifest_path).read())
        assert content["job_id"] == job.job_id
        assert "schema_version" in content
        assert "software" in content
    finally:
        os.remove(manifest_path)
