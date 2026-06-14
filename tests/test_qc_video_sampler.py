"""Tests for QC video frame sampler."""
import pytest
import tempfile
import shutil
from pathlib import Path
from src.merchandiser.qc.qc_video_sampler import sample_video_frames, normalize_video_input_to_frames

_FIXTURE_PNG = "tests/fixtures/multimodal/red_square.png"

def test_sample_video_frames_from_file_returns_single_frame():
    frames = sample_video_frames(_FIXTURE_PNG)
    assert frames == [_FIXTURE_PNG]

def test_sample_video_frames_from_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(3):
            shutil.copy(_FIXTURE_PNG, Path(tmpdir) / f"frame_{i:03d}.png")
        frames = sample_video_frames(tmpdir, max_frames=5)
    assert len(frames) == 3

def test_sample_video_frames_max_frames_respected():
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(10):
            shutil.copy(_FIXTURE_PNG, Path(tmpdir) / f"frame_{i:03d}.png")
        frames = sample_video_frames(tmpdir, max_frames=4)
    assert len(frames) == 4

def test_sample_video_frames_nonexistent_returns_empty():
    frames = sample_video_frames("path/does/not/exist.mp4")
    assert frames == []

def test_normalize_video_input_prefers_provided_frames():
    provided = [_FIXTURE_PNG]
    frames = normalize_video_input_to_frames(video_frames=provided)
    assert frames == provided

def test_normalize_video_input_from_path():
    frames = normalize_video_input_to_frames(video_path=_FIXTURE_PNG)
    assert frames == [_FIXTURE_PNG]

def test_normalize_video_input_empty_returns_empty():
    frames = normalize_video_input_to_frames()
    assert frames == []
