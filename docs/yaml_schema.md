# 剧本 YAML Schema 设计说明

本文档定义 `novel2script` 生成的剧本 YAML 结构。Schema 文件位于 `schemas/script.schema.json`，使用 JSON Schema Draft 2020-12 描述 YAML 解析后的数据对象。

## 顶层结构

```yaml
schema_version: 1.0.0
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

## 设计原因

1. **面向编辑而不是终稿排版**：YAML 比传统剧本排版更容易被作者、编辑器和 AI 工具继续修改，因此 Schema 保留结构化字段，而不是直接生成固定版式。
2. **保持来源可追溯**：`source.chapter_count`、`source.chapters` 和 `scene.source_chapter` 让作者能快速定位每个场景来自哪一章，降低改编校对成本。
3. **兼顾编剧工作流**：`acts -> scenes -> blocks` 对应从宏观结构到场景执行的常见剧本工作方式，便于逐层修改。
4. **允许 AI 与人工协作**：`summary`、`beats`、`revision_notes` 明确标记 AI 生成的中间判断，作者可以选择接受、删除或重写。
5. **便于程序校验**：字段采用稳定 ID、枚举类型和最小长度约束，可在 CLI 或 CI 中自动检查，避免生成半结构化、难以复用的 YAML。
