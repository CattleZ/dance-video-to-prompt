"""Agent 模式工作包 AGENT_INSTRUCTIONS 生成。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def write_agent_kit(
    out_dir: Path,
    video_path: Path,
    duration: float,
    samples: list,
    interval: float,
    rhythm: dict | None = None,
    quality: dict | None = None,
) -> None:
    """为 Skill/Agent 模式写入工作包（不调用模型）。"""
    quality = quality or {}
    q_frames = {f.get("path"): f for f in (quality.get("frames") or []) if f.get("path")}
    frame_lines = []
    for s in samples:
        q = q_frames.get(str(s.path), {})
        st = q.get("status", "?")
        sc = q.get("score", "?")
        tag = f" [{st} score={sc}]"
        frame_lines.append(f"- t={s.time_sec:.2f}s | {s.path}{tag}")
    frame_lines_text = "\n".join(frame_lines)

    sharp_list = quality.get("sharp_for_analysis") or [str(s.path) for s in samples]
    sharp_lines = "\n".join(f"- {p}" for p in sharp_list)
    blurry = quality.get("blurry_remaining") or []
    blur_lines = (
        "\n".join(
            f"- t={b.get('time_sec')}s score={b.get('score')} | {b.get('path')}"
            for b in blurry
        )
        if blurry
        else "- （无）"
    )
    q_stats = quality.get("stats") or {}
    quality_line = (
        f"- 清晰度：sharp={q_stats.get('sharp')} rescued={q_stats.get('rescued')} "
        f"blurry={q_stats.get('blurry')} thr={quality.get('threshold')} "
        f"→ `{out_dir / 'frame_quality.json'}` / `{out_dir / 'frame_quality_brief.md'}`"
    )

    skill_tpl = ROOT / "skills" / "dance-video-to-prompt" / "templates"
    template_path = skill_tpl / "output_template.md"
    if not template_path.exists():
        template_path = ROOT / "templates" / "output_template.md"
    schema_path = skill_tpl / "stage1_schema.json"
    if not schema_path.exists():
        schema_path = ROOT / "templates" / "stage1_schema.json"
    template_text = (
        template_path.read_text(encoding="utf-8") if template_path.exists() else ""
    )
    schema_text = (
        schema_path.read_text(encoding="utf-8") if schema_path.exists() else "{}"
    )

    rhythm = rhythm or {}
    rhythm_ok = bool(rhythm.get("ok"))
    bpm = rhythm.get("bpm")
    rhythm_line = (
        f"- 节奏分析：成功 BPM≈{bpm} → `{out_dir / 'rhythm_analysis.json'}` / "
        f"`{out_dir / 'rhythm_brief.md'}`"
        if rhythm_ok
        else f"- 节奏分析：失败或无音轨（{rhythm.get('error')}）→ 仍读 "
        f"`{out_dir / 'rhythm_analysis.json'}`，融合时不强行假 BPM"
    )

    instructions = f"""# Agent 工作包（不调用外部视觉 API）

请使用 **当前 CLI Agent 的多模态看图能力**（read_file 读取图片）完成**画面分析**；  
节奏数值已由本地脚本写好，须由 **节奏子代理** 解释，再由主代理 **融合** 写 Prompt。  
不要再调用 HTTP/Vision API。

## 输入

- 视频：`{video_path}`
- 时长：约 {duration:.2f} 秒
- 抽帧间隔：{interval:.3f}s
- 帧数：{len(samples)}
- 输出目录：`{out_dir}`
{quality_line}
{rhythm_line}

## 关键帧清晰度（看图前必读）

脚本已用 Laplacian 方差检测模糊，并对模糊帧做**邻帧救援**（替换文件）。

### 优先分析列表 `sharp_for_analysis`（必须优先 read_file 这些）

{sharp_lines}

### 仍模糊帧（不要细抠手指/五官；可写运动模糊）

{blur_lines}

**规则：**
1. **先读** `frame_quality.json` / `frame_quality_brief.md`
2. **优先**只对 `sharp_for_analysis` 做精细肢体与表情描述
3. 模糊帧：只记时间轴占位与大致姿态，**禁止编造**清晰手型/眉眼细节
4. 若仍模糊帧过多（>25%）：动作写趋势与幅度，细节标注「运动模糊不可确认」；可建议用户 `--interval 0.25` 重抽

## 全部关键帧列表（含清晰度标签）

{frame_lines_text}

## 强制多阶段流程（清晰度 → 画面 ∥ 节奏 → 融合）

### 阶段 0：确认清晰度（已由脚本完成，Agent 须遵守结果）

- 报告：`{out_dir / "frame_quality.json"}`
- 不得忽略 blurry 标签硬编细节

### 阶段 A：画面代理 — 事实观察（只描述，不创作）

1. **优先**按 `sharp_for_analysis` 用 read_file 阅读；帧多则首尾+均匀覆盖清晰帧。
2. 只写画面能确认的内容，禁止编造；模糊帧不编造细节。
3. 写入：`{out_dir / "analysis.json"}`
4. JSON 对齐 schema：

```json
{schema_text}
```

要求：
- segments 按 0.5~1.5 秒切分，覆盖全片
- 每段 action：左右肢、角度/幅度、手型、视线
- 每段 expression：眉/眼/口/情绪 + 相对上段变化；禁止「表情自然」
- 对话/字幕无则写「无」
- audio_guess 可粗写；**最终 BPM 以节奏文件为准，禁止画面代理编造精确拍点表**

### 阶段 B：节奏子代理 — 卡点规划（可与 A 并行）

1. 只读：`{out_dir / "rhythm_analysis.json"}`、`{out_dir / "rhythm_brief.md"}`
2. 角色说明见 skill：`skills/dance-video-to-prompt/agents/rhythm_agent.md`
3. **不要**用看帧代替节奏数字；**不要**直接写 prompt.md
4. 写入：`{out_dir / "rhythm_plan.json"}`（结构见 templates/rhythm_plan_schema.json）

可用 spawn_subagent 独立完成阶段 B；无 spawn 则主会话切换角色完成。

### 阶段 C：融合 — 6 段生成提示词（主代理）

**同时基于** `analysis.json` + `rhythm_plan.json`（及 rhythm_analysis 拍点表）写出 Prompt。

必须严格 6 个二级标题（不要增删）：

## 视觉风格
## 场景叙述
## 摄影技术
## 动作清单
## 对话/文字
## 背景声音

写作规范：
- 准确：不编造 analysis 中没有的关键动作/服装/场景/表情
- 动作五要素：左右肢、角度/幅度、手型、视线、面部表情；禁止空泛词
- **若节奏 ok**：动作时间对齐拍点/accent；强拍写踩实/微顿/甩肢等；背景声音写清 BPM 与卡点秒数
- **若节奏失败**：不强行假 BPM，动作跟画面时间轴
- 摄影技术：摄影机 / 镜头 / 灯光 / 情绪
- 简体中文

模板参考：

```markdown
{template_text}
```

写入：`{out_dir / "prompt.md"}`

### 阶段 D：校验

- 画面：无编造、左右正确、五要素齐全、表情有变化或写保持
- 清晰度：未对 blurry 帧编造精细手型/五官
- 节奏：ok 时 BPM 与大卡点是否进入动作清单与背景声音
- 覆盖写回 `prompt.md`

## 完成标准

- [ ] 已读 frame_quality.json，优先分析 sharp_for_analysis
- [ ] analysis.json 合法（含 segments[].expression）
- [ ] rhythm_plan.json 已写（节奏失败时也要有保守 plan）
- [ ] prompt.md 含完整 6 段标题
- [ ] 动作清单五要素齐全；有节奏则体现卡点
- [ ] 向用户打印 prompt.md，并给出 analysis / frame_quality / rhythm_* / frames 路径
"""
    (out_dir / "AGENT_INSTRUCTIONS.md").write_text(instructions, encoding="utf-8")

