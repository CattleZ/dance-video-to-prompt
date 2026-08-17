---
name: dance-video-to-prompt
description: >
  把本地短视频（跳舞/姿态展示/变装/旅行打卡/穿搭行走等，优先 ≤10s，更长也可）反推成
  「可直接用于 AI 视频生成」的结构化中文提示词。
  固定输出 6 段：视觉风格、场景叙述、摄影技术、动作清单、对话/文字、背景声音。
  流水线含：密帧抽帧、关键帧清晰度检测与邻帧救援、本地音轨节奏分析（BPM/拍点）、
  画面事实观察、节奏子代理、画面×节奏融合；看图须分析面部表情；动作五要素强制细化。
  模糊帧不编造手指/五官细节。本 Skill 走 Agent 多模态看图，节奏与清晰度由本地脚本产出。
  Triggers / 触发词：/dance-video-to-prompt、跳舞视频转提示词、视频反推 prompt、卡点提示词、
  视频节奏分析、动作总结生成提示词、短视频生成提示词、变装视频提示词、姿态视频提示词、
  dance video to prompt、video to prompt、把这个视频写成生成提示词。
---

# 跳舞/姿态短视频 → 视频生成提示词

## 一句话说明

**本地视频 → 抽帧 → 清晰度检测/救援 → 节奏脚本 →（画面代理 ∥ 节奏子代理）→ 融合 → 6 段 Prompt。**  
目标是服务「用 AI 再生成类似/卡点增强视频」，不是动捕或跟跳评分。

## 适用场景

| 适合 | 不适合 |
|------|--------|
| 跳舞、轻舞、卡点姿态 | 精确动捕/关节坐标 |
| 变装、穿搭行走、多场景 | 长片全片逐镜（可拆段） |
| 输出给可灵/Runway/即梦 | 直接自动成片（本 Skill 只出 Prompt） |

**时长建议**：优先 ≤10s；10~20s 可做；更长建议拆段。

## 固定输出结构（不可增删标题）

1. **视觉风格**  
2. **场景叙述**  
3. **摄影技术**  
4. **动作清单**（含表情 + **卡点对齐**）  
5. **对话/文字**  
6. **背景声音**（含 **BPM** 与拍点关系）  

契约：`references/output_contract.md`  
模板：`templates/output_template.md`  
节奏子代理：`agents/rhythm_agent.md`

## 多角色分工（强制）

```text
主 Agent（编排）
 ├─ 本地脚本：抽帧 → 清晰度检测/邻帧救援 → 节奏分析
 ├─ 画面代理：优先 read 清晰帧 → analysis.json
 ├─ 节奏子代理：读 rhythm_* → rhythm_plan.json
 └─ 融合：analysis + rhythm_plan → prompt.md → 校验
```

| 角色 | 输入 | 输出 | 禁止 |
|------|------|------|------|
| **抽帧脚本** | 视频 | `frames/`、`frames_meta.json` | 调模型 |
| **清晰度脚本** | 帧+视频 | `frame_quality.json`、救援覆盖模糊 jpg | 调模型 |
| **节奏脚本** | 视频 | `rhythm_analysis.json`、`rhythm_brief.md`、`audio.wav` | 编造画面 |
| **画面代理** | **优先** `sharp_for_analysis` | `analysis.json` | 对模糊帧编造手/脸细节；编造精确 BPM |
| **节奏子代理** | rhythm 脚本产物 | `rhythm_plan.json` | 编造服装动作细节 |
| **融合（主）** | analysis + rhythm_plan | `prompt.md` | 跳过节奏/清晰度约束 |

**子代理调用建议（Grok/支持 Task 的环境）：**

```text
spawn_subagent(
  subagent_type="general-purpose",
  description="节奏卡点规划",
  prompt="你是节奏子代理。只读 OUT_DIR 下 rhythm_analysis.json 与 rhythm_brief.md，
  严格按 skills/.../agents/rhythm_agent.md 输出 rhythm_plan.json 到 OUT_DIR。
  不要读关键帧，不要写 prompt.md。"
)
```

无 spawn 时：主 Agent **切换角色**完成节奏子代理步骤，再融合。

## 面部表情 / 动作五要素

同前版强制规范：眉眼口 + 情绪变化；每条动作含 **左右肢、角度/幅度、手型、视线、面部表情**。  
详见 `references/output_contract.md`。

## 重要原则

1. **不要调用** 外部 Vision HTTP API（除非用户明确要求 API 版）。  
2. **必须用** `read_file` 看关键帧做画面分析。  
3. **节奏数值以脚本为准**；子代理只做解释与卡点策略，不改 BPM 造假。  
4. **融合强制**：有 `ok=true` 的节奏结果时，动作清单与「背景声音」必须贴合拍点。  
5. 准确优先：画面事实 > 卡点增强时机/力度；不编造不存在的服装道具。

## 路径解析

| 位置 | 含义 |
|------|------|
| `<repo>/skills/dance-video-to-prompt/` | **主副本** |
| `<repo>/.grok/skills/...` | 项目 Grok |
| `~/.grok/skills/...` | 用户 Grok |
| `~/.agents/skills/...` / `~/.claude/skills/...` | 其它 Agent |

`REPO_ROOT`：`DANCE_VIDEO_PROMPT_ROOT` → skill 上两级/三级 → 自动解析为当前仓库根

## 工作流（必须按序）

### Step 0：确认输入

- 本地视频**绝对路径**  
- 可选：`--interval`（默认 0.33）、`--max-frames`（默认 36）

### Step 1：抽帧 + 清晰度 + 节奏（无模型 API）

```bash
bash "<SKILL_DIR>/scripts/run_extract.sh" "<视频绝对路径>" --interval 0.33 --max-frames 36
```

`run_extract` / `main.py` **自动**完成：

1. 抽帧 → `frames/`  
2. **清晰度检测**（Laplacian 方差）+ **邻帧救援** → `frame_quality.json`  
3. 节奏分析 → `rhythm_analysis.json`  

记下：`OUT_DIR`、`FRAME_COUNT`、`QUALITY_OK`、`SHARP`/`RESCUED`/`BLURRY`、`RHYTHM_OK`、`BPM`。

仅补跑清晰度（可选）：

```bash
bash "<REPO_ROOT>/scripts/check_frame_quality.sh" "<视频>" "<OUT_DIR>"
```

### Step 1.5：清晰度处理规则（强制）

| 检测结果 | 自动处理 | Agent 看图时 |
|----------|----------|--------------|
| **sharp** | 保留 | 正常精细描述 |
| **rescued** | 用 ±0.03~0.15s 邻帧中最清晰者**覆盖原 jpg** | 按救援后图像描述；时间轴仍用原抽帧时刻 |
| **blurry**（救援失败） | 保留原帧并标记 | **禁止**编造手指/五官；只写大致姿态；可写「运动模糊」 |
| 模糊帧 **>25%** | `QUALITY_OK=0` | 细节降置信；可建议 `--interval 0.25` 重抽 |

**阈值**：`max(35, 中位数 × 0.40)`（自适应 + 绝对下限）。

### Step 2：读工作包

1. `OUT_DIR/AGENT_INSTRUCTIONS.md`  
2. `OUT_DIR/frame_quality.json`、`frame_quality_brief.md`（**先于看图**）  
3. `OUT_DIR/frames_meta.json`  
4. `OUT_DIR/rhythm_analysis.json`、`rhythm_brief.md`  
5. skill 内 templates + `references/output_contract.md` + `agents/rhythm_agent.md`

### Step 3A：画面代理 — 事实观察

- **优先** `read_file` `frame_quality.json` → `sharp_for_analysis` 列表  
- 模糊路径不细抠手脸  
- 写入 `OUT_DIR/analysis.json`  
- 音乐字段可粗写；**BPM 以节奏文件为准**

### Step 3B：节奏子代理 — 卡点规划

- 按 `agents/rhythm_agent.md`  
- 写入 `OUT_DIR/rhythm_plan.json`  
- 可与 3A **并行**（spawn 时）

### Step 4：融合 — 6 段 Prompt

合并 `analysis.json` + `rhythm_plan.json`：

- 动作时间轴对齐拍点 / accent  
- 强拍写清重音动作  
- 「背景声音」写入 BPM、能量弧、卡点秒数  
- 严格 6 个 `##` 标题 → `OUT_DIR/prompt.md`

### Step 5：校验

- 画面：无编造、左右正确、五要素齐全  
- 节奏：`ok=true` 时 BPM 与大卡点是否进 prompt  
- 覆盖写回 `prompt.md`

### Step 6：交付

1. 打印完整 `prompt.md`  
2. 路径：`prompt.md`、`analysis.json`、`rhythm_analysis.json`、`rhythm_plan.json`、`frames/`  
3. 提示：可人工扫帧；长片拆段生成  

## 输出示例（动作条含卡点）

```markdown
## 动作清单
1. 0.05–0.67秒（第1–2拍）：左腿支撑；右脚强拍落地……；面部：……；卡点：踩实。
2. 10.62–11.24秒（大卡点）：……；卡点：顿步半拍。

## 背景声音
- 音乐：……约 96.5 BPM……
- 混音与卡点：一拍一步；大卡点 5.03/10.0/10.62s
```

## 与 API 版

| 版本 | 何时用 |
|------|--------|
| **本 Skill（Agent）** | 默认；含节奏子代理 + 融合 |
| **API 版** | `bash scripts/analyze_api.sh`；仍建议先 `analyze_rhythm.sh` 把节奏 JSON 并入上下文 |

## 失败处理

| 情况 | 处理 |
|------|------|
| 帧数为 0 | 转码 mp4 后重试 |
| 大量运动模糊 | 自动邻帧救援；仍糊则降细节置信；`--interval 0.25` 重抽 |
| 节奏 ok=false | 不写假 BPM；动作跟画面时间轴 |
| 帧过多 | 在 **sharp** 集合内均匀 12~16 帧细看 |
| 原片动作不卡点 | 生成侧按节奏**增强卡点**，背景声音说明 |

## 安装同步

```bash
bash skills/dance-video-to-prompt/scripts/install.sh
```
