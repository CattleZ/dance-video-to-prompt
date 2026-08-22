# dance-video-to-prompt

把 **本地短视频**（跳舞 / 姿态 / 变装 / 旅行打卡 / 穿搭行走等，优先 ≤10s）反推成可直接用于 AI 视频生成的结构化 Prompt。

仓库：https://github.com/CattleZ/dance-video-to-prompt

能力包含：密帧抽帧、**关键帧清晰度检测与邻帧救援**、**音轨节奏/BPM 分析**、画面事实观察、节奏卡点融合、7 段生成提示词。  
看图须分析 **人物身材特征**、**穿搭颜色与样式**、**拍摄场景**、**拍摄方法 / 运镜 / 关注重点** 与面部表情。  
动作清单强制含：**左右肢、角度/幅度、手型、视线、面部表情（含变化）**。

## 快速开始

```bash
# 1. 环境
bash scripts/setup.sh

# 2. 抽帧 + 清晰度 + 节奏（Agent 模式工作包）
bash skills/dance-video-to-prompt/scripts/run_extract.sh /path/to/video.mp4

# 3. 安装 Skill 到本机 Grok / Claude 目录（可选）
bash skills/dance-video-to-prompt/scripts/install.sh
```

输出目录默认在 `output/<视频名>_<时间戳>/`（该目录不入库）。

## 输出模板（固定 7 段）

| 模块 | 作用 |
|------|------|
| 视觉风格 | 画质、构图、光影、色调 |
| 场景叙述 | 人物（含身材体型特征）、穿搭（颜色与样式）、气质 |
| 拍摄场景 | 场所、空间关系、背景、地面、陈设、时空与环境光 |
| 摄影技术 | 拍摄方法、运镜、关注重点、机位、焦段、灯光、情绪 |
| 动作清单 | 带时间；**强制**含左右肢、角度/幅度、手型、视线 |
| 对话/文字 | 对白与字幕 |
| 背景声音 | BGM 风格、BPM 与卡点关系 |

---

## 两个版本

| | **A. Skill / Agent 版（推荐默认）** | **B. CLI / API 版** |
|--|-------------------------------------|---------------------|
| 谁做「看懂画面」 | **当前 CLI Agent 的多模态看图** | 外部视觉模型 HTTP API |
| 是否调 Vision API | **否** | 是 |
| 适用 | 交互式、准确可控、免配 API | 批量、无人值守、CI |
| 入口 | Skill `dance-video-to-prompt` 或 `extract_frames.sh` | `analyze_api.sh` |
| 模型依赖 | 会话里的 Grok/Claude 等（能 read 图片） | `VISION_MODEL` + 网关 Token |

两种版本 **共用**：

- 抽帧逻辑（密帧）
- 三阶段流程（事实 → 模板 Prompt → 校验）
- 同一套 7 段输出契约

```text
本地视频
   │
   ▼
 scripts/extract_frames.sh     ← 共用，无 API
   │
   ├──────────── Agent/Skill 版 ────────────┐
   │  Agent read_file 看帧                   │
   │  → analysis.json → prompt.md            │
   │                                         │
   └──────────── API 版 ─────────────────────┤
      analyze_api.sh → Vision API 三阶段 ────┘
```

---

## A. Skill / Agent 版（不调 API）

### 方式 1：在 Grok/CLI 里用 Skill

触发示例：

- `/dance-video-to-prompt`
- 「把这个跳舞视频反推成生成提示词：/path/to/a.mp4」

Agent 会：

1. 运行抽帧脚本
2. 自己看关键帧图片
3. 写出 `analysis.json` + `prompt.md`

**Skill 主副本（随仓库复用）：**

```text
skills/dance-video-to-prompt/
```

同步到本机各 Agent（修改 skill 后请再执行）：

```bash
bash skills/dance-video-to-prompt/scripts/install.sh
```

会安装到：

- `.grok/skills/dance-video-to-prompt/`（项目 Grok 发现）
- `~/.grok/skills/dance-video-to-prompt/`
- `~/.agents/skills/dance-video-to-prompt/`
- `~/.claude/skills/dance-video-to-prompt/`（若存在）

### 方式 2：手动只抽帧，再让 Agent 继续

```bash
bash scripts/setup.sh   # 首次
bash scripts/extract_frames.sh /path/to/dance.mp4
# 或
bash scripts/analyze.sh /path/to/dance.mp4 --mode agent
```

输出目录内会有：

- `frames/` — 关键帧
- `frames_meta.json`
- `AGENT_INSTRUCTIONS.md` — 给 Agent 的完整步骤

然后在对话里让 Agent「按 AGENT_INSTRUCTIONS 完成分析」。

---

## B. CLI / API 版（调视觉 API）

```bash
# 1. 配置
cp config/settings.example.env config/settings.env
# 填写 ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN / VISION_MODEL
# VISION_MODEL 必须支持看图

# 2. 一键分析
bash scripts/analyze_api.sh /path/to/dance.mp4

# 更高精度抽帧
bash scripts/analyze_api.sh /path/to/dance.mp4 --interval 0.25

# 跳过校验轮（更快）
bash scripts/analyze_api.sh /path/to/dance.mp4 --no-verify
```

---

## 输出目录

```text
output/<视频名>_<时间戳>/
  frames/
  frames_meta.json
  AGENT_INSTRUCTIONS.md   # 仅 agent 模式
  analysis.json             # 分析完成后
  prompt.md                 # 最终可复制 Prompt
  run_meta.json             # 仅 api 模式
```

`output/` 为运行产物，默认不提交到 Git。

---

## 流水线（准确率）

1. **高密度抽帧**（默认 0.33s，可 0.25s）
2. **清晰度检测 + 邻帧救援**
3. **节奏分析**（BPM / 拍点）
4. **阶段一**：事实观察 → JSON（含身材、穿搭、拍摄场景、运镜、表情）
5. **阶段二**：改写 7 段生成 Prompt
6. **阶段三**：对照事实校验

不做关节坐标级动作重建；动作以可生成的时间轴文字为准。

---

## 依赖

- Python 3.10+
- `opencv` + `Pillow`（抽帧，两种模式都要）
- `httpx`（仅 API 模式）

```bash
bash scripts/setup.sh
```

---

## 脚本一览

| 脚本 | 作用 |
|------|------|
| `scripts/setup.sh` | 安装依赖 |
| `scripts/extract_frames.sh` | 只抽帧 + Agent 工作包 |
| `scripts/check_frame_quality.sh` | 关键帧清晰度检测与邻帧救援 |
| `scripts/analyze_rhythm.sh` | 音轨节奏 / BPM 分析 |
| `scripts/analyze.sh` | 通用入口（`--mode agent\|api`） |
| `scripts/analyze_api.sh` | API 全自动 |
| `skills/dance-video-to-prompt/scripts/run_extract.sh` | Skill 入口：抽帧 + 清晰度 + 节奏 |
| `skills/dance-video-to-prompt/scripts/install.sh` | 同步 Skill 到本机 Agent 目录 |
