"""
QC video sampler — samples frames from video files or accepts pre-sampled frame paths.
Does not require OpenCV or FFmpeg for MVP. Uses pre-extracted frame paths.
"""
import os
from pathlib import Path
from src.m_side.m_event_logger import log_m_event


def sample_video_frames(
    video_path: str,
    max_frames: int = 8,
    project_id: str | None = None,
) -> list[str]:
    """
    Sample frames from a video file.

    MVP: If the path is a directory, treats contained .jpg/.png as pre-extracted frames.
    If the path is a file, returns it as a single-frame list (real sampling requires FFmpeg).

    Returns list of frame paths.
    """
    p = Path(video_path)
    frames: list[str] = []

    if p.is_dir():
        candidates = sorted(p.glob("*.jpg")) + sorted(p.glob("*.png"))
        frames = [str(f) for f in candidates[:max_frames]]
    elif p.is_file():
        # MVP: treat the file itself as a single frame (for testing)
        frames = [video_path]
    else:
        # Path doesn't exist — return empty, log warning
        log_m_event(
            event_type="QC_VIDEO_SAMPLER_PATH_NOT_FOUND",
            b_workspace_id=project_id or "unknown",
            payload={"video_path": video_path},
        )
        return []

    if project_id:
        log_m_event(
            event_type="QC_VIDEO_FRAMES_SAMPLED",
            b_workspace_id=project_id,
            payload={"video_path": video_path, "frames_sampled": len(frames), "max_frames": max_frames},
        )
    return frames


def normalize_video_input_to_frames(
    video_frames: list[str] | None = None,
    video_path: str | None = None,
    max_frames: int = 8,
    project_id: str | None = None,
) -> list[str]:
    """
    Normalize video input to a list of frame paths.

    If video_frames is provided and non-empty, return them (already sampled).
    If video_path is provided, sample from it.
    Otherwise return empty list.
    """
    if video_frames:
        return list(video_frames[:max_frames])
    if video_path:
        return sample_video_frames(video_path, max_frames=max_frames, project_id=project_id)
    return []
