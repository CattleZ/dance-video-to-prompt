#!/usr/bin/env python3
"""抽帧清晰度检测：Laplacian 方差 + 邻帧救援替换模糊帧。"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
from PIL import Image

from extract_frames import FrameSample

logger = logging.getLogger("frame_quality")

# 绝对下限：低于此值几乎一定糊（与分辨率有关，救援后再判）
ABS_MIN_SHARP = 35.0
# 相对中位数比例：score < median * REL_FACTOR 视为模糊
REL_FACTOR = 0.40
# 救援搜索偏移（秒）
RESCUE_OFFSETS = (-0.10, -0.06, -0.03, 0.03, 0.06, 0.10, 0.15, -0.15)
# 救援成功需至少比原帧好这么多倍
RESCUE_IMPROVE = 1.25


@dataclass
class FrameQuality:
    index: int
    time_sec: float
    path: str
    score: float
    status: str  # sharp | rescued | blurry
    rescued_offset: float | None = None
    score_before: float | None = None


def laplacian_score_bgr(frame_bgr) -> float:
    if frame_bgr is None or frame_bgr.size == 0:
        return 0.0
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def laplacian_score_path(path: Path) -> float:
    img = cv2.imread(str(path))
    if img is None:
        return 0.0
    return laplacian_score_bgr(img)


def _read_frame_at(cap: cv2.VideoCapture, time_sec: float, fps: float, frame_count: int):
    idx = min(int(round(time_sec * fps)), max(frame_count - 1, 0))
    if idx < 0:
        idx = 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, frame = cap.read()
    if not ok or frame is None:
        return None, idx
    return frame, idx


def _adaptive_threshold(scores: list[float]) -> float:
    if not scores:
        return ABS_MIN_SHARP
    arr = sorted(scores)
    mid = arr[len(arr) // 2]
    # 中位数偏低时用绝对门槛兜底
    return max(ABS_MIN_SHARP, mid * REL_FACTOR)


def check_and_rescue_frames(
    video_path: Path,
    samples: list[FrameSample],
    output_dir: Path,
    duration: float,
) -> dict[str, Any]:
    """
    检测每帧清晰度；模糊则在邻域重抽最清晰一帧覆盖原文件。
    写入 frame_quality.json，返回报告 dict。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    if not samples:
        report = {
            "ok": False,
            "error": "无帧可检",
            "frames": [],
            "sharp_for_analysis": [],
            "blurry_remaining": [],
            "stats": {},
        }
        _write_report(output_dir, report)
        return report

    # 初筛分数
    raw_scores = [laplacian_score_path(s.path) for s in samples]
    threshold = _adaptive_threshold(raw_scores)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        report = {
            "ok": False,
            "error": f"无法打开视频做救援: {video_path}",
            "threshold": threshold,
            "frames": [],
            "sharp_for_analysis": [str(s.path) for s in samples],
            "blurry_remaining": [],
            "stats": {"total": len(samples), "note": "跳过救援"},
        }
        _write_report(output_dir, report)
        return report

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    results: list[FrameQuality] = []
    for s, score0 in zip(samples, raw_scores):
        if score0 >= threshold:
            results.append(
                FrameQuality(
                    index=s.index,
                    time_sec=s.time_sec,
                    path=str(s.path),
                    score=round(score0, 2),
                    status="sharp",
                )
            )
            continue

        # 邻帧救援
        best_score = score0
        best_frame = None
        best_off = 0.0
        for off in RESCUE_OFFSETS:
            t2 = s.time_sec + off
            if t2 < 0 or t2 > duration + 0.05:
                continue
            frame, _ = _read_frame_at(cap, t2, fps, frame_count)
            if frame is None:
                continue
            sc = laplacian_score_bgr(frame)
            if sc > best_score:
                best_score = sc
                best_frame = frame
                best_off = off

        if best_frame is not None and best_score >= score0 * RESCUE_IMPROVE and best_score >= threshold * 0.85:
            rgb = cv2.cvtColor(best_frame, cv2.COLOR_BGR2RGB)
            Image.fromarray(rgb).save(s.path, quality=92, optimize=True)
            # 更新 sample 时间标注：文件名可保留原时刻，报告记真实偏移
            results.append(
                FrameQuality(
                    index=s.index,
                    time_sec=s.time_sec,
                    path=str(s.path),
                    score=round(best_score, 2),
                    status="rescued",
                    rescued_offset=round(best_off, 3),
                    score_before=round(score0, 2),
                )
            )
            logger.info(
                "模糊帧已救援 t=%.2fs score %.1f→%.1f offset=%+.3fs",
                s.time_sec,
                score0,
                best_score,
                best_off,
            )
        else:
            results.append(
                FrameQuality(
                    index=s.index,
                    time_sec=s.time_sec,
                    path=str(s.path),
                    score=round(score0, 2),
                    status="blurry",
                    score_before=round(score0, 2),
                )
            )
            logger.warning("帧仍模糊 t=%.2fs score=%.1f thr=%.1f", s.time_sec, score0, threshold)

    cap.release()

    sharp_paths = [r.path for r in results if r.status in ("sharp", "rescued")]
    blurry = [r for r in results if r.status == "blurry"]
    # 若清晰帧过少：把相对最清晰的补进分析列表（并标注仍糊）
    min_need = max(4, len(samples) // 3)
    if len(sharp_paths) < min_need:
        ranked = sorted(results, key=lambda x: x.score, reverse=True)
        for r in ranked:
            if r.path not in sharp_paths:
                sharp_paths.append(r.path)
            if len(sharp_paths) >= min_need:
                break

    n_sharp = sum(1 for r in results if r.status == "sharp")
    n_rescued = sum(1 for r in results if r.status == "rescued")
    n_blur = len(blurry)
    ok = n_blur <= max(2, len(samples) // 4) and len(sharp_paths) >= 3

    report: dict[str, Any] = {
        "ok": ok,
        "method": "laplacian_variance",
        "threshold": round(threshold, 2),
        "rel_factor": REL_FACTOR,
        "abs_min": ABS_MIN_SHARP,
        "rescue_offsets_sec": list(RESCUE_OFFSETS),
        "frames": [asdict(r) for r in results],
        "sharp_for_analysis": sharp_paths,
        "blurry_remaining": [asdict(r) for r in blurry],
        "stats": {
            "total": len(results),
            "sharp": n_sharp,
            "rescued": n_rescued,
            "blurry": n_blur,
            "sharp_for_analysis_count": len(sharp_paths),
            "mean_score": round(sum(r.score for r in results) / max(len(results), 1), 2),
        },
        "agent_rules": {
            "prefer_paths": "sharp_for_analysis",
            "blurry_use": "仅作时间占位，不据此写细手指/五官；可写「运动模糊/动作过渡」",
            "if_many_blurry": "动作条写幅度与趋势，细节降置信；可建议用户 --interval 0.25 重抽",
        },
    }
    _write_report(output_dir, report)
    _write_brief(output_dir, report)
    logger.info(
        "清晰度: total=%d sharp=%d rescued=%d blurry=%d thr=%.1f ok=%s",
        len(results),
        n_sharp,
        n_rescued,
        n_blur,
        threshold,
        ok,
    )
    return report


def _write_report(out_dir: Path, report: dict[str, Any]) -> None:
    (out_dir / "frame_quality.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _write_brief(out_dir: Path, report: dict[str, Any]) -> None:
    st = report.get("stats") or {}
    lines = [
        "# 关键帧清晰度简报",
        "",
        f"- 方法：Laplacian 方差",
        f"- 阈值：{report.get('threshold')}",
        f"- 统计：共 {st.get('total')} 帧 | 清晰 {st.get('sharp')} | 救援 {st.get('rescued')} | 仍模糊 {st.get('blurry')}",
        f"- 供分析优先帧数：{st.get('sharp_for_analysis_count')}",
        f"- 状态 ok：{report.get('ok')}",
        "",
        "## 仍模糊的时刻（勿细抠手指五官）",
    ]
    blur = report.get("blurry_remaining") or []
    if not blur:
        lines.append("- （无）")
    else:
        for r in blur:
            lines.append(f"- t={r.get('time_sec')}s score={r.get('score')} → `{r.get('path')}`")
    lines += [
        "",
        "## 画面代理规则",
        "1. **优先** read_file `sharp_for_analysis` 列表中的路径",
        "2. 模糊帧：可记时间与大致姿态，**不要**编造清晰手型/五官细节",
        "3. 若 blurry 过多：动作清单写趋势与幅度，细节写「因运动模糊不可确认」",
        "",
    ]
    (out_dir / "frame_quality_brief.md").write_text("\n".join(lines), encoding="utf-8")
