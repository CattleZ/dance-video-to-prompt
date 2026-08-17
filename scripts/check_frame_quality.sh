#!/usr/bin/env bash
# 对已有 OUT_DIR 的 frames/ 重新做清晰度检测与邻帧救援
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ $# -lt 2 ]]; then
  echo "用法: bash scripts/check_frame_quality.sh <视频路径> <OUT_DIR>"
  exit 1
fi

PYTHON="python3"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

export PYTHONUNBUFFERED=1
exec "$PYTHON" - <<PY
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path("$ROOT") / "src"))
from extract_frames import FrameSample
from frame_quality import check_and_rescue_frames

video = Path("$1").expanduser().resolve()
out_dir = Path("$2").expanduser().resolve()
meta_path = out_dir / "frames_meta.json"
if not meta_path.exists():
    raise SystemExit(f"缺少 {meta_path}，请先抽帧")
meta = json.loads(meta_path.read_text(encoding="utf-8"))
samples = []
for i, f in enumerate(meta.get("frames") or []):
    p = Path(f["path"])
    samples.append(
        FrameSample(
            index=i,
            time_sec=float(f["time_sec"]),
            path=p,
            width=int(f.get("w") or 0),
            height=int(f.get("h") or 0),
        )
    )
duration = float(meta.get("duration_sec") or 0)
report = check_and_rescue_frames(video, samples, out_dir, duration)
st = report.get("stats") or {}
print(f"QUALITY_OK={1 if report.get('ok') else 0}")
print(f"SHARP={st.get('sharp')} RESCUED={st.get('rescued')} BLURRY={st.get('blurry')}")
print(f"QUALITY_JSON={out_dir / 'frame_quality.json'}")
PY
