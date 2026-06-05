# AI 小说转剧本工具

面向小说作者的 AI 辅助改编工具，可将 3 个章节以上的小说文本转换为结构化剧本 YAML 初稿。工具默认使用本地启发式改编引擎，保证无外部 API Key 时也能运行；配置 OpenAI 兼容接口后，可使用大模型增强场景摘要、人物提取和对白润色。

## 功能

- 自动识别 `第 1 章`、`Chapter 1`、Markdown 标题等章节边界。
- 要求至少 3 个章节输入，避免把短片段误当作完整改编任务。
- 将小说段落拆解为幕、场景、动作、对白和转场说明。
- 输出可编辑 YAML，并提供 JSON Schema 校验。
- 生成 `structure_map`，把开场、诱发事件、中点、高潮和结局映射到具体场景。
- 生成 `story_bible`，整理人物连续性、地点、道具/线索和待解问题。
- 生成 `adaptation_report`，汇总章节覆盖、场景映射、结构指标、质量风险和修订清单。
- 生成 `coverage_report`，按专业 coverage 思路给出推荐等级、分项评分、强弱项和优先修订动作。
- 支持 Fountain 剧本文本导出，便于进入专业剧本编辑器继续打磨。
- 支持 CLI 批处理，适合持续迭代剧本初稿。

## 安装

发布包：

```powershell
python -m pip install novel2script
```

需要 OpenAI 兼容模型增强时安装可选依赖：

```powershell
python -m pip install "novel2script[ai]"
```

本地开发：

```powershell
python -m pip install -e .[dev]
```

安装后可直接使用 CLI 或模块入口：

```powershell
novel2script --version
python -m novel2script --version
novel2script examples/three_chapters.txt --output outputs/fog-city.yaml --validate
```

## 使用

```powershell
novel2script examples/three_chapters.txt --output outputs/fog-city.yaml
```

也可以直接验证输出是否符合 Schema：

```powershell
novel2script examples/three_chapters.txt --output outputs/fog-city.yaml --validate
```

需要导出剧本文本时，可以选择 Fountain：

```powershell
novel2script examples/three_chapters.txt --format fountain --output outputs/fog-city.fountain
```

如果当前 shell 找不到 console script，也可以使用模块入口：

```powershell
python -m novel2script examples/three_chapters.txt --output outputs/fog-city.yaml --validate
```

## 可选 AI 增强

设置环境变量后启用 OpenAI 兼容模型：

```powershell
$env:OPENAI_API_KEY="sk-..."
novel2script examples/three_chapters.txt --provider openai --model gpt-4.1-mini
```

如果没有配置 Key，工具会自动回退到本地启发式引擎。

默认本地模式不会调用外部 AI 服务。启用 `--provider openai` 且设置 `OPENAI_API_KEY`
后，工具会把截断后的章节摘要和本地生成的 baseline JSON 发送给 OpenAI 兼容接口；
处理私有手稿前请先阅读 [隐私说明](PRIVACY.md)。

## 依赖与原创说明

第三方依赖：

- `PyYAML`：安全生成 YAML 文本。
- `jsonschema`：校验输出结构。
- `openai`：可选的大模型增强接口。
- `pytest`、`ruff`：开发测试与代码检查。

原创功能部分包括章节解析、小说段落到剧本块的启发式转换、YAML Schema 设计、CLI 工作流和测试样例。

## 文档

- [YAML Schema 设计文档](docs/yaml_schema.md)
- [竞品调研与改进记录](docs/market_research.md)
- [发布检查清单](docs/release_checklist.md)
- [变更日志](CHANGELOG.md)
- [贡献指南](CONTRIBUTING.md)
- [隐私说明](PRIVACY.md)
- [安全策略](SECURITY.md)
- [JSON Schema 文件](schemas/script.schema.json)

## 工程化状态

- CI 在 PR 和 `main` push 上运行 ruff、pytest、CLI smoke test、Schema 同步检查、包构建检查、Windows smoke 和依赖安全审计。
- 发布 workflow 监听 `v*.*.*` 标签，校验标签版本、构建 wheel/sdist、安装 wheel/sdist 做 smoke test，并通过 PyPI Trusted Publishing 发布；PyPI 发布成功后创建 GitHub Release。
- Dependabot 每周检查 Python 依赖和 GitHub Actions 更新。
- 发布前请先在 PyPI 配置 `pypi` environment 的 Trusted Publisher。
