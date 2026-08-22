---
name: dance-video-to-prompt
description: >
  把本地短视频（跳舞/姿态展示/变装/旅行打卡/穿搭行走等，优先 ≤10s，更长也可）反推成
  「可直接用于 AI 视频生成」的结构化中文提示词。
  固定输出 7 段：视觉风格、场景叙述、拍摄场景、摄影技术、动作清单、对话/文字、背景声音。
  流水线含：密帧抽帧、关键帧清晰度检测与邻帧救援、本地音轨节奏分析（BPM/拍点）、
  画面事实观察、节奏子代理、画面×节奏融合；看图须分析**人物身材特征**、**穿搭颜色与样式**、
  **拍摄场景**、**拍摄方法/运镜/关注重点**与面部表情；动作五要素强制细化。模糊帧不编造手指/五官/精确身材轮廓。本 Skill 走 Agent
  多模态看图，节奏与清晰度由本地脚本产出。
  Triggers / 触发词：/dance-video-to-prompt、跳舞视频转提示词、视频反推 prompt、卡点提示词、
  视频节奏分析、动作总结生成提示词、短视频生成提示词、变装视频提示词、姿态视频提示词、
  dance video to prompt、video to prompt、把这个视频写成生成提示词。
---

# 跳舞/姿态短视频 → 视频生成提示词

## 一句话说明

**本地视频 → 抽帧 → 清晰度检测/救援 → 节奏脚本 →（画面代理 ∥ 节奏子代理）→ 融合 → 7 段 Prompt。**  
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
2. **场景叙述**（人物身材 + **穿搭颜色与样式**）  
3. **拍摄场景**（场所、空间关系、背景、陈设）  
4. **摄影技术**（含 **拍摄方法、运镜、关注重点**）  
5. **动作清单**（含表情 + **卡点对齐**）  
6. **对话/文字**  
7. **背景声音**（含 **BPM** 与拍点关系）  

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
| **画面代理** | **优先** `sharp_for_analysis` | `analysis.json` | 对模糊帧编造手/脸/精确身材轮廓；编造精确 BPM |
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

## 人物身材 / 穿搭 / 拍摄场景 / 拍摄运镜 / 面部表情 / 动作五要素

### 身材特征（强制，主写「场景叙述」）

看图与 `analysis.json` 必须填写：

| 字段 | 内容 |
|------|------|
| `subject.body_type` | 整体体型（高矮 + 胖瘦/曲线类型） |
| `subject.body_proportions` | 头身比、腿长、肩胯、腰线等比例 |
| `subject.body_details` | 肩颈/胸廓/腰腹/臀胯/腿/手臂等分部位（可见才写） |
| `subject.posture_habit` | 挺拔、微塌腰、含胸等体态习惯 |
| `segments[].body_focus` | 本段突出的身材或体态焦点 |

融合进 `prompt.md` 时：**场景叙述**须有连续、可复现的身材描写（整体体型 + ≥2 项分部位/比例 + 体态），禁止「身材好/很瘦」空话。  
身材锚点主放场景叙述；动作清单仅在体态相关处轻点，不整段重复。

### 穿搭颜色与样式（强制，主写「场景叙述」）

看图与 `analysis.json` 必须填写 `subject.outfit`：

| 字段 | 内容 |
|------|------|
| `summary` | 整体穿搭一句话（必须含颜色与款式） |
| `style` | 风格标签（OL / 甜妹 / 运动 / 泳装 / JK 等） |
| `palette` | 主色 + 辅色 + 点缀 |
| `items[]` | 可见单品：`slot` + `name` + **`color`** + **`style`（款式/剪裁）** |
| `change` | 无 / 变装时刻与前后 |

融合时：**逐件**写出颜色与款式（剪裁/长短/腰线），禁止「时尚穿搭」或只写「白衬衫黑裙」不写剪裁。  
详见 `references/output_contract.md`。

### 拍摄场景（强制，独立成段「拍摄场景」）

记录「拍的是什么地方」，不并入场景叙述、不与运镜混写。`analysis.json` 的 `scene` 至少填写：

| 字段 | 内容 |
|------|------|
| `setting_type` / `location` / `space` | 室内外、地点类型、空间结构 |
| `subject_placement` | 人物站位与朝向 |
| `background` / `ground` | 背景与地面（含颜色或材质） |
| `props` / `atmosphere` | 陈设、空间气质 |
| `time_weather` / `ambient_light` | 时段天气、空间光源位置 |
| `changes` | 单场景贯穿 / 切场时间点 |

融合进 `prompt.md` 时必须含：**场所 + 空间关系 + 背景 + 地面 + 陈设 + 时空与环境光 + 氛围 + 场景变化**。  
禁止「场景好看」；不编造未见地标。

### 拍摄方法 / 运镜 / 关注重点（强制，主写「摄影技术」）

跨帧对比推断镜头语言；`analysis.json` 的 `camera` 至少填写：

| 字段 | 内容 |
|------|------|
| `camera.shot_method` | 拍摄方法综述（设备稳定 + 机位 + 意图） |
| `camera.movement` | 主运镜类型与路径/速度 |
| `camera.movement_rhythm` | 运镜与拍点关系 |
| `camera.focus_priority` | 全片镜头关注重点（主+次） |
| `camera.height` / `angle` / `framing` | 机位高度、角度、景别构图 |
| `camera.device_feel` / `depth_of_field` | 设备质感、景深合焦 |
| `segments[].shot_size` / `camera_move` / `shot_focus` | 分段景别、运镜、关注点 |

融合进 `prompt.md` 时，**摄影技术**必须含：

1. **拍摄方法** — 怎么拍、机位与稳定、想突出什么  
2. **运镜** — 可执行的方向/推拉/跟随（禁止「运镜流畅」）  
3. **关注重点** — 镜头优先拍全身比例 / 腿脚 / 腰胯 / 手势 / 面部 / 服装 / 环境中的哪些  

有节奏时尽量写「强拍微顿镜头 / 弱拍跟移」。切镜须标明，勿伪装连续长镜头。

### 面部表情与动作五要素

眉眼口 + 情绪变化；每条动作含 **左右肢、角度/幅度、手型、视线、面部表情**。  

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
| **blurry**（救援失败） | 保留原帧并标记 | **禁止**编造手指/五官/精确身材轮廓；只写大致姿态与体型印象；可写「运动模糊」 |
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
- 模糊路径不细抠手脸与精确身材轮廓  
- **强制观察身材**：整体体型、比例、分部位轮廓、体态 → 写入 `subject.body_*` / `posture_habit`  
- **强制观察穿搭**：风格标签、配色、逐件颜色+款式/剪裁 → 写入 `subject.outfit`；变装填 `change` 与 `segments[].outfit_note`  
- **强制观察拍摄场景**：室内外、地点类型、空间结构、人物站位、背景/地面（含颜色材质）、陈设、时空与环境光 → 写入 `scene.*`；切场填 `changes` 与 `segments[].scene_note`  
- **强制观察摄影/运镜**（须跨帧对比）：  
  - 设备与稳定感、机位高度/角度、景别构图  
  - 运镜类型与路径（推拉/横移/跟随/固定/环绕等）  
  - **关注重点**：镜头在展示全身、腿脚、腰胯、手势、面部、服装还是环境  
  - 写入 `camera.shot_method` / `movement` / `focus_priority` 等；分段填 `shot_size` / `camera_move` / `shot_focus`  
- 各段填写 `body_focus`（本段画面突出的身材/体态）  
- 写入 `OUT_DIR/analysis.json`（字段对齐 `templates/stage1_schema.json`）  
- 音乐字段可粗写；**BPM 以节奏文件为准**

### Step 3B：节奏子代理 — 卡点规划

- 按 `agents/rhythm_agent.md`  
- 写入 `OUT_DIR/rhythm_plan.json`  
- 可与 3A **并行**（spawn 时）

### Step 4：融合 — 7 段 Prompt

合并 `analysis.json` + `rhythm_plan.json`：

- **场景叙述**合并 `body_type` + `body_proportions` + `body_details` + `posture_habit` + 发型 + `outfit`（逐件颜色与款式），形成人物身份锚点；**不写环境细节**  
- **拍摄场景**合并 `scene.setting_type` / `location` / `space` / `subject_placement` / `background` / `ground` / `props` / `time_weather` / `ambient_light` / `atmosphere` / `changes`  
- **摄影技术**合并 `camera.shot_method` + `movement` + `focus_priority` + 机位/镜头/灯光；有节奏则叠加运镜卡点（强拍微顿等）  
- 动作时间轴对齐拍点 / accent  
- 强拍写清重音动作；体态相关动作可呼应 `body_focus`；焦点变化可轻点 `shot_focus`  
- 「背景声音」写入 BPM、能量弧、卡点秒数  
- 严格 7 个 `##` 标题 → `OUT_DIR/prompt.md`

### Step 5：校验

- 身材：场景叙述含整体体型 + ≥2 项分部位/比例 + 体态；无空话；未见不编  
- 穿搭：逐件颜色 + 款式；有风格标签；无「时尚穿搭」空话  
- 拍摄场景：独立成段；场所 + 背景 ≥2 元素 + 人物站位；未与场景叙述/摄影技术重复  
- 摄影：含拍摄方法 + 可执行运镜 + 关注重点；无「运镜流畅」空话；切镜未伪装长镜头  
- 画面：无编造、左右正确、五要素齐全  
- 节奏：`ok=true` 时 BPM 与大卡点是否进 prompt  
- 覆盖写回 `prompt.md`

### Step 6：交付

1. 打印完整 `prompt.md`  
2. 路径：`prompt.md`、`analysis.json`、`rhythm_analysis.json`、`rhythm_plan.json`、`frames/`  
3. 提示：可人工扫帧；长片拆段生成  

## 输出示例（身材 + 穿搭 + 拍摄场景 + 摄影运镜 + 动作卡点）

```markdown
## 场景叙述
一位身材高挑纤细的年轻女性，头身比修长、腿长占比高，窄肩锁骨清晰，腰肢纤细、小腹平坦，
胯线利落，细长直腿，手臂纤细，站姿挺拔略带舞蹈感；浅棕长卷发齐肩；
身着 OL 职场风：白色修身短袖翻领衬衫、领口扣好，黑色高腰包臀迷你裙，黑色漆皮尖头细高跟鞋。

## 拍摄场景
- 场所：室内楼梯间过道，狭长空间
- 空间关系：人物靠右侧灰白墙，距半开白门约半步，面朝镜头
- 背景：灰白墙面有铅笔涂鸦，黑色踢脚，右侧半开白门
- 地面：水泥灰地
- 陈设与道具：半开白门；双手握透明冰咖杯
- 时空与环境光：白天室内，顶灯一块过曝
- 氛围：冷灰职场过道
- 场景变化：单场景贯穿

## 摄影技术
- 拍摄方法：竖屏手机+轻云台感，眼平略偏低机位正面偏 3/4 侧，始终框住全身以突出腿长与体态线条
- 运镜：主体居中缓慢跟拍；强拍处镜头微顿半拍，弱拍轻微横移跟随胯线
- 关注重点：主焦点全身比例与站姿；次焦点脚步踩点与裙摆；表情段落短暂抬景别至半身
- 摄影机：眼平微低、正面略侧、稳定器级平滑
- 镜头：全身主景别，背景轻度虚化，人物居中留顶安全距
- 灯光：……
- 情绪：清爽、卡点、自信

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
