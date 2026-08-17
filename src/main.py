#!/usr/bin/env python3
"""CLI：本地短视频 → 6 段结构化视频生成提示词。

支持两种模式：
- agent：只抽帧并写出 Agent 工作说明（不调 API，给 Skill/CLI 模型看图用）
- api：抽帧 + 视觉 API 三阶段分析
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze_rhythm import analyze_video_rhythm  # noqa: E402
from extract_frames import extract_frames  # noqa: E402
from frame_quality import check_and_rescue_frames  # noqa: E402


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "analyze.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


from agent_kit import write_agent_kit  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="将 ≤10s 本地跳舞视频反推为 6 段视频生成提示词"
    )
    p.add_argument("video", type=Path, help="本地视频路径")
    p.add_argument(
        "--mode",
        choices=("agent", "api"),
        default="agent",
        help="agent=只抽帧+工作包(默认，给 Skill/CLI 模型)；api=调用视觉 API",
    )
    p.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="输出目录，默认 output/<视频名>_<时间戳>",
    )
    p.add_argument(
        "--interval",
        type=float,
        default=None,
        help="抽帧间隔秒，默认 FRAME_INTERVAL 或 0.33",
    )
    p.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="最多帧数，默认 MAX_FRAMES 或 36",
    )
    p.add_argument(
        "--model",
        type=str,
        default=None,
        help="[api] 视觉模型名",
    )
    p.add_argument(
        "--no-verify",
        action="store_true",
        help="[api] 跳过第三轮校验",
    )
    p.add_argument(
        "--frames-only",
        action="store_true",
        help="兼容旧参数：等价于 --mode agent，且不写详细说明时可忽略",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_env_file(ROOT / "config" / "settings.env")

    setup_logging(ROOT / "logs")
    logger = logging.getLogger("main")

    mode = "agent" if args.frames_only else args.mode

    video_path: Path = args.video.expanduser().resolve()
    if not video_path.exists():
        logger.error("视频不存在: %s", video_path)
        return 1

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else ROOT / "output" / f"{video_path.stem}_{stamp}"
    )
    frames_dir = out_dir / "frames"
    out_dir.mkdir(parents=True, exist_ok=True)

    interval = args.interval or float(os.getenv("FRAME_INTERVAL", "0.33"))
    max_frames = args.max_frames or int(os.getenv("MAX_FRAMES", "36"))

    logger.info("模式: %s", mode)
    logger.info("视频: %s", video_path)
    logger.info("输出: %s", out_dir)
    logger.info("抽帧间隔=%.3fs max_frames=%d", interval, max_frames)

    samples, duration = extract_frames(
        video_path=video_path,
        output_dir=frames_dir,
        interval_sec=interval,
        max_frames=max_frames,
    )

    # 看图前：清晰度检测 + 邻帧救援
    logger.info("开始关键帧清晰度检测…")
    quality = check_and_rescue_frames(
        video_path=video_path,
        samples=samples,
        output_dir=out_dir,
        duration=duration,
    )
    q_by_path = {f["path"]: f for f in (quality.get("frames") or [])}
    logger.info(
        "清晰度完成: sharp=%s rescued=%s blurry=%s ok=%s",
        (quality.get("stats") or {}).get("sharp"),
        (quality.get("stats") or {}).get("rescued"),
        (quality.get("stats") or {}).get("blurry"),
        quality.get("ok"),
    )

    meta = {
        "video": str(video_path),
        "duration_sec": duration,
        "interval_sec": interval,
        "mode": mode,
        "frame_quality_ok": quality.get("ok"),
        "frame_quality_threshold": quality.get("threshold"),
        "frames": [
            {
                "time_sec": s.time_sec,
                "path": str(s.path),
                "w": s.width,
                "h": s.height,
                "sharpness": (q_by_path.get(str(s.path)) or {}).get("score"),
                "quality_status": (q_by_path.get(str(s.path)) or {}).get("status"),
            }
            for s in samples
        ],
        "sharp_for_analysis": quality.get("sharp_for_analysis") or [],
    }
    (out_dir / "frames_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 抽帧后统一做节奏分析（agent / api 均落盘，供融合使用）
    logger.info("开始节奏分析…")
    rhythm = analyze_video_rhythm(video_path=video_path, out_dir=out_dir, keep_wav=True)
    logger.info(
        "节奏分析完成: ok=%s bpm=%s",
        rhythm.get("ok"),
        rhythm.get("bpm"),
    )

    if mode == "agent":
        write_agent_kit(
            out_dir,
            video_path,
            duration,
            samples,
            interval,
            rhythm=rhythm,
            quality=quality,
        )
        logger.info("Agent 模式：抽帧+清晰度+节奏完成，共 %d 帧", len(samples))
        logger.info("工作说明: %s", out_dir / "AGENT_INSTRUCTIONS.md")
        print(str(out_dir))
        print(f"FRAME_COUNT={len(samples)}")
        print(f"DURATION_SEC={duration:.3f}")
        print(f"QUALITY_OK={1 if quality.get('ok') else 0}")
        print(f"SHARP={(quality.get('stats') or {}).get('sharp')}")
        print(f"RESCUED={(quality.get('stats') or {}).get('rescued')}")
        print(f"BLURRY={(quality.get('stats') or {}).get('blurry')}")
        print(f"RHYTHM_OK={1 if rhythm.get('ok') else 0}")
        print(f"BPM={rhythm.get('bpm')}")
        print(f"QUALITY_JSON={out_dir / 'frame_quality.json'}")
        print(f"RHYTHM_JSON={out_dir / 'rhythm_analysis.json'}")
        print(f"INSTRUCTIONS={out_dir / 'AGENT_INSTRUCTIONS.md'}")
        return 0

    # API 模式：优先把清晰帧送给视觉模型
    from analyze import analyze_video_to_prompt  # noqa: WPS433
    from llm_client import VisionLLMClient  # noqa: WPS433

    sharp_set = set(quality.get("sharp_for_analysis") or [])
    if sharp_set:
        samples_for_api = [s for s in samples if str(s.path) in sharp_set] or samples
    else:
        samples_for_api = samples

    client = VisionLLMClient(model=args.model)
    result = analyze_video_to_prompt(
        client=client,
        samples=samples_for_api,
        duration=duration,
        video_name=video_path.name,
        verify=not args.no_verify,
        rhythm=rhythm,
    )

    prompt_path = out_dir / "prompt.md"
    analysis_path = out_dir / "analysis.json"
    prompt_path.write_text(result["prompt_md"], encoding="utf-8")
    analysis_path.write_text(
        json.dumps(result["analysis"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "run_meta.json").write_text(
        json.dumps(
            {
                "video": str(video_path),
                "duration_sec": result["duration"],
                "frame_count": result["frame_count"],
                "model": client.model,
                "mode": "api",
                "issues": result["issues"],
                "verify": not args.no_verify,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    logger.info("提示词已写入: %s", prompt_path)
    if result["issues"]:
        logger.warning("结构问题: %s", "; ".join(result["issues"]))

    print("\n========== 视频生成提示词 ==========\n")
    print(result["prompt_md"])
    print("====================================")
    print(f"\n已保存: {prompt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
