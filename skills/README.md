# 项目 Skills

本目录存放可复用的 Agent Skill，方便随仓库一起拷贝/同步。

## dance-video-to-prompt

**本地短视频 → 7 段 AI 视频生成提示词**（Agent 看图，不调外部 Vision API）。

覆盖：跳舞 / 姿态展示 / 变装 / 旅行打卡 / 穿搭行走等多类竖屏参考片。  
动作清单强制包含：**左右肢、角度/幅度、手型、视线、面部表情（含时间轴变化）**。  
看图时须分析眉/眼/口与情绪、**穿搭颜色与样式**、**拍摄场景**，写入 `analysis.json` 并落到 Prompt。

### 主副本

```text
skills/dance-video-to-prompt/
```

完整说明见该目录下 `SKILL.md`。

### 安装到本机各 Agent

```bash
bash skills/dance-video-to-prompt/scripts/install.sh
```

同步到：

- `.grok/skills/dance-video-to-prompt/`
- `~/.grok/skills/dance-video-to-prompt/`
- `~/.agents/skills/dance-video-to-prompt/`
- `~/.claude/skills/dance-video-to-prompt/`（若存在）

### 使用

```text
/dance-video-to-prompt /path/to/video.mp4
```

或：

```text
把这个跳舞视频反推成生成提示词：/path/to/video.mp4
```

只抽帧：

```bash
bash skills/dance-video-to-prompt/scripts/run_extract.sh /path/to/video.mp4
```

### 维护

**以 `skills/dance-video-to-prompt/` 为主副本**；改完请再跑 `install.sh`。
