# 竞品调研与改进记录

调研日期：2026-06-05

本次调研关注“小说作者如何把长篇文本改编成可继续打磨的剧本初稿”。我们优先查看官方产品页或官方帮助文档，并把公开页面没有明确覆盖的能力作为改进机会。

## 调研对象

| 产品 | 官方定位/能力摘要 | 对本项目的启发 |
| --- | --- | --- |
| Sudowrite | 官方文档列出 Write、Describe、Rewrite、Brainstorm、First Draft、Scenes 和 Draft 等小说写作能力。 | 强在小说续写、扩写和章节生成，但公开说明更偏“生成/润色文本”，没有突出小说章节到剧本场景的结构化可追溯输出。 |
| Novelcrafter | 官网强调 Codex、规划模式、协作、自定义提示和多模型接入。 | 强在故事资料管理和长篇创作规划，但公开说明更偏小说项目管理，没有把“原章节覆盖率”和“改编质检报告”作为核心输出。 |
| Squibler | 官网强调 full-length book generation、full-length screenplay generation、outline、AI Smart Writer、elements 和 visuals。 | 能生成完整书稿或剧本，但公开说明更偏端到端生成和编辑，没有明确提供面向作者校对的章节到场景映射。 |
| Final Draft | 官方功能页强调专业剧本格式、Beat Board、Outline Editor 和 Structure Lines。 | 强在专业剧本写作、排版和大纲，不是小说改编工具，缺少从小说原文自动生成可追溯 YAML 的工作流。 |
| Celtx | 官网强调剧本编辑、制片管理、协作和前期制作流程。 | 强在制片前期管理，适合已有剧本后的生产流程；小说到剧本初稿的章节覆盖和质量检查仍可作为本项目差异化。 |
| FinalBit / NolanAI | 官网定位为 AI screenwriting、budgeting 与 pre-production 的一体化平台。 | 强在影视生产链路整合，但公开页面重点是编剧、预算和前期制作，没有展示小说章节改编的 YAML Schema 与覆盖报告。 |
| StudioBinder | 官网强调 script breakdown、shooting schedule、call sheet、shot list 和 storyboard 等制片管理能力。 | 强在已有剧本后的拆解和生产排期，但并不解决小说原文到剧本初稿阶段的人物、地点、道具/线索资料沉淀。 |
| WriterDuet / Arc Studio 等剧本编辑器 | 同类剧本编辑器通常强调专业排版、多人协作、云端编辑和导入导出。 | 作者拿到 YAML 后仍需要一个能进入专业剧本编辑器的文本稿，因此结构化输出之外还需要轻量格式互操作。 |

## 发现的不足

1. **缺少源文本可追溯性**：很多工具能生成小说、剧本或大纲，但公开页面没有把“每个剧本场景来自哪一章”作为一等字段。
2. **缺少改编覆盖率**：作者很难判断 AI 是否漏掉某章、某条关键线索或某个转折。
3. **缺少可机器校验的中间产物**：常见输出是富文本、编辑器文档或完整剧本，而不是可由 CI/脚本校验的 YAML。
4. **缺少面向二次打磨的质检清单**：生成初稿后，作者仍需要知道哪里对白太少、地点不明确、场景数量不足。
5. **缺少改编资产沉淀**：影视改编不只需要剧本文本，还需要人物连续性、地点、美术线索、关键道具和未解决问题的资料库；这类能力通常分散在小说资料库工具或制片拆解工具中。
6. **缺少格式互操作**：结构化 YAML 适合校验和二次处理，但作者也需要可导入或复制到专业剧本工具的纯文本剧本格式。

## 已落地改进

本项目新增 `adaptation_report` 字段，作为结构化剧本 YAML 的改编质检报告：

- `chapter_coverage`：统计总章节、已改编章节、覆盖率和缺失章节。
- `scene_map`：将小说章节映射到生成场景，便于逐章核对。
- `metrics`：统计场景数、文本块数、动作块数、对白块数和对白比例。
- `quality_flags`：自动提示对白过少、地点待定、章节缺失等风险。
- `revision_checklist`：给作者下一轮人工打磨清单。

该改进让工具从“生成一个剧本初稿”升级为“生成一个可追溯、可校验、可继续打磨的改编包”。

进一步调研后，本项目新增 `story_bible` 字段，补充可复用的改编资料库：

- `characters`：记录角色功能、首次出现场景和连续性复核提示。
- `locations`：记录地点和关联场景，帮助后续美术设定和场景调度。
- `props`：记录道具/线索、来源章节和戏剧功能，避免关键物件在改编中丢失。
- `open_questions`：列出作者需要继续回答的结构问题。

再进一步调研剧本编辑器后，本项目新增 Fountain 导出：

- 保留 YAML 作为可校验的结构化源文件。
- 通过 `--format fountain` 输出剧本文本，包含标题、logline、场景标题、来源章节注释、动作、对白和转场。
- 让作者可以把初稿带入专业剧本写作工具继续排版、协作和润色。

## 参考来源

- Sudowrite Features: https://docs.sudowrite.com/getting-started/dQph1snuwbfMWG9wRjsNug/features/dq7YUMNy5ZMvKUJiRAisyT
- Novelcrafter: https://www.novelcrafter.com/
- Squibler: https://www.squibler.io/
- Final Draft Features: https://www.finaldraft.com/products/features/
- Celtx: https://www.celtx.com/
- FinalBit / NolanAI: https://www.finalbitai.com/
- StudioBinder: https://www.studiobinder.com/
- WriterDuet: https://www.writerduet.com/
- Arc Studio: https://www.arcstudiopro.com/
