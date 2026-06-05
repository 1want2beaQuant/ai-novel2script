# 剧本 YAML Schema 设计说明

本文档定义 `novel2script` 生成的剧本 YAML 结构。Schema 文件位于 `schemas/script.schema.json`，使用 JSON Schema Draft 2020-12 描述 YAML 解析后的数据对象。

## 顶层结构

```yaml
schema_version: 1.3.0
title: 雾城来信
language: zh-CN
generated_at: 2026-06-05T00:00:00+00:00
source:
  type: novel
  chapter_count: 3
  chapters:
    - index: 1
      title: 第 1 章 雨夜来信
logline: ...
themes:
  - 悬疑
characters:
  - name: 林晚
    role: protagonist
    description: ...
    first_seen_scene: S001
acts:
  - id: A1
    title: 开端
    purpose: 建立人物、目标与改编世界。
    scenes: []
structure_map:
  model: five_point_screenplay_map
  beats:
    - id: opening_image
      label: 开场意象
      scene_id: S001
      source_chapter: 1
      summary: 林晚在书房里发现一封旧信。
      purpose: 建立主角处境、基调和世界入口。
      revision_hint: 强化第一场的视觉动作，减少背景说明。 当前映射到 S001。
  diagnostics:
    - 场景数量少于五个，五点结构中的部分节拍会共用场景。
story_bible:
  characters:
    - name: 林晚
      role: protagonist
      first_seen_scene: S001
      continuity_note: 复核林晚在各章节中的目标、关系和称呼是否一致。
  locations:
    - name: 书房
      scene_ids:
        - S001
      note: 可作为场景调度和美术设定线索。
  props:
    - name: 信
      source_chapters:
        - 1
      dramatic_function: 承载线索、关系或转折，需要在后续剧本中保持出现和回收。
  open_questions:
    - 主角在每一幕的外在目标和内在需求是否已经明确？
adaptation_report:
  chapter_coverage:
    total_chapters: 3
    adapted_chapters: 3
    coverage_ratio: 1.0
    missing_chapters: []
  scene_map:
    - chapter_index: 1
      chapter_title: 第 1 章 雨夜来信
      scene_id: S001
      scene_title: 第 1 章 雨夜来信
  metrics:
    scene_count: 3
    block_count: 12
    action_blocks: 6
    dialogue_blocks: 3
    dialogue_ratio: 0.25
  quality_flags:
    - 未发现结构性风险，建议进入人物动机和对白语气复核。
  revision_checklist:
    - 逐项核对 scene_map，确认每个小说章节都有对应剧本场景。
revision_notes:
  - ...
```

## 字段定义

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `schema_version` | string | Schema 版本，使用语义化版本号，便于后续升级。 |
| `title` | string | 剧本标题，可由用户指定或从第一章推断。 |
| `language` | string | 输出语言，例如 `zh-CN`。 |
| `generated_at` | string | ISO 8601 生成时间，便于追踪改编批次。 |
| `source` | object | 原小说来源摘要，必须包含章节数量和章节标题列表。 |
| `logline` | string | 一句话故事梗概，帮助作者快速判断改编方向。 |
| `themes` | string[] | 主题标签，用于后续润色和检索。 |
| `characters` | object[] | 人物表，描述角色功能及首次出现场景。 |
| `acts` | object[] | 幕结构，每幕包含多个场景。 |
| `structure_map` | object | 五点结构地图，把关键节拍映射到场景并给出结构诊断。 |
| `story_bible` | object | 改编资料库，整理人物连续性、地点、道具/线索和待解问题。 |
| `adaptation_report` | object | 改编质检报告，说明章节覆盖、场景映射、结构指标、质量风险和修订清单。 |
| `revision_notes` | string[] | 自动改编后的修订提醒。 |

## 场景结构

每个场景包含 `id`、`title`、`location`、`time`、`summary`、`source_chapter`、`characters`、`beats` 和 `blocks`。

- `id` 采用 `S001` 格式，稳定、短小，适合人工批注。
- `source_chapter` 保留小说章节索引，保证改编稿可以追溯到原文。
- `beats` 是场景节拍，给作者提供继续扩写的情节点。
- `blocks` 是可拍摄文本单元，支持动作、对白、旁白和转场。

## 文本块结构

`blocks` 中的每个元素代表一个剧本块：

```yaml
- type: dialogue
  character: 林晚
  text: 这不是父亲的笔迹。
```

`type` 可选值：

- `action`：动作或场面描写。
- `dialogue`：人物对白，必须包含 `character`。
- `voice_over`：旁白或内心独白。
- `transition`：转场提示。

## 改编报告结构

`adaptation_report` 用于解决 AI 改编常见的“生成了内容但不知道覆盖了哪些原文章节”的问题。

- `chapter_coverage` 记录总章节数、已改编章节数、覆盖率和缺失章节。
- `scene_map` 将每个源章节映射到生成场景，便于作者回到原文核对。
- `metrics` 统计场景数、文本块数、动作块数、对白块数和对白比例。
- `quality_flags` 给出自动发现的结构风险，例如对白过少或地点待定。
- `revision_checklist` 给出下一轮人工打磨建议。

## 改编资料库结构

`story_bible` 用于把剧本初稿沉淀成可继续开发的资料库：

- `characters` 记录人物名称、角色功能、首次出现场景和连续性复核提示。
- `locations` 记录场景地点、关联场景 ID 和美术/调度提示。
- `props` 记录道具或线索、来源章节和戏剧功能，避免关键线索丢失。
- `open_questions` 汇总需要作者继续回答的改编问题。

## 结构地图

`structure_map` 用于帮助作者检查剧本初稿是否具备基本的结构节拍：

- `model` 当前为 `five_point_screenplay_map`。
- `beats` 固定包含开场意象、诱发事件、中点转折、高潮和结局。
- 每个节拍记录 `scene_id`、`source_chapter`、摘要、功能和修订提示。
- `diagnostics` 自动指出节拍是否过度集中在少数场景，帮助作者扩写或重排章节。

## 设计原因

1. **面向编辑而不是终稿排版**：YAML 比传统剧本排版更容易被作者、编辑器和 AI 工具继续修改，因此 Schema 保留结构化字段，而不是直接生成固定版式。
2. **保持来源可追溯**：`source.chapter_count`、`source.chapters` 和 `scene.source_chapter` 让作者能快速定位每个场景来自哪一章，降低改编校对成本。
3. **兼顾编剧工作流**：`acts -> scenes -> blocks` 对应从宏观结构到场景执行的常见剧本工作方式，便于逐层修改。
4. **允许 AI 与人工协作**：`summary`、`beats`、`revision_notes` 明确标记 AI 生成的中间判断，作者可以选择接受、删除或重写。
5. **补足改编质检**：`adaptation_report` 让作者知道哪些章节已经被改成场景、哪里还缺对白或具体地点，避免只拿到一个不可追溯的 AI 初稿。
6. **沉淀改编资产**：`story_bible` 把人物、地点、道具和未解决问题独立出来，便于作者后续扩写、统一设定或进入制片拆解。
7. **检查结构节拍**：`structure_map` 把大纲工具中的 Beat Board/Story Map 思路引入改编初稿，帮助作者判断关键转折是否已经落到具体场景。
8. **便于程序校验**：字段采用稳定 ID、枚举类型和最小长度约束，可在 CLI 或 CI 中自动检查，避免生成半结构化、难以复用的 YAML。
