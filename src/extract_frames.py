"""从本地短视频高密度抽取关键帧。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class FrameSample:
    index: int
    time_sec: float
    path: Path
    width: int
    height: int


def extract_frames(
    video_path: Path,
    output_dir: Path,
    interval_sec: float = 0.33,
    max_frames: int = 36,
) -> tuple[list[FrameSample], float]:
    """
    按固定时间间隔抽帧，并保证包含首尾帧。
    返回 (帧列表, 视频时长秒)。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / fps if frame_count > 0 else 0.0

    if duration <= 0:
        # 回退：逐帧读取估算
        duration = _probe_duration_by_read(cap, fps)
        cap.release()
        cap = cv2.VideoCapture(str(video_path))

    if duration <= 0:
        cap.release()
        raise RuntimeError(f"无法读取视频时长: {video_path}")

    # 目标时间点：均匀间隔 + 首尾
    times: list[float] = []
    t = 0.0
    while t < duration - 1e-6:
        times.append(round(t, 3))
        t += interval_sec
    end_t = round(max(duration - 1.0 / fps, 0.0), 3)
    if not times or abs(times[-1] - end_t) > 0.05:
        times.append(end_t)

    # 过多则均匀下采样，始终保留首尾
    if len(times) > max_frames:
        times = _downsample_keep_ends(times, max_frames)

    samples: list[FrameSample] = []
    for i, time_sec in enumerate(times):
        frame_idx = min(int(time_sec * fps), max(frame_count - 1, 0))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok or frame is None:
            logger.warning("跳过无法读取的帧 t=%.3fs idx=%s", time_sec, frame_idx)
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        out_path = output_dir / f"frame_{i:03d}_{time_sec:.2f}s.jpg"
        Image.fromarray(rgb).save(out_path, quality=90, optimize=True)
        samples.append(
            FrameSample(
                index=i,
                time_sec=time_sec,
                path=out_path,
                width=w,
                height=h,
            )
        )

    cap.release()
    if not samples:
        raise RuntimeError(f"未能抽取任何帧: {video_path}")

    logger.info(
        "抽帧完成: duration=%.2fs frames=%d interval=%.2fs",
        duration,
        len(samples),
        interval_sec,
    )
    return samples, duration


def _downsample_keep_ends(times: list[float], max_frames: int) -> list[float]:
    if max_frames < 2:
        return [times[0]]
    if len(times) <= max_frames:
        return times
    # 首尾固定，中间均匀取
    inner_n = max_frames - 2
    if inner_n <= 0:
        return [times[0], times[-1]]
    step = (len(times) - 1) / (inner_n + 1)
    mids = [times[int(round(step * (i + 1)))] for i in range(inner_n)]
    result = [times[0]] + mids + [times[-1]]
    # 去重保序
    dedup: list[float] = []
    for x in result:
        if not dedup or abs(dedup[-1] - x) > 1e-6:
            dedup.append(x)
    return dedup


def _probe_duration_by_read(cap: cv2.VideoCapture, fps: float) -> float:
    n = 0
    while True:
        ok, _ = cap.read()
        if not ok:
            break
        n += 1
    return n / fps if fps > 0 else 0.0
