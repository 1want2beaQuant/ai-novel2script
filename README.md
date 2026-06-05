# AI 小说转剧本工具

面向小说作者的 AI 辅助改编工具，可将 3 个章节以上的小说文本转换为结构化剧本 YAML 初稿。工具默认使用本地启发式改编引擎，保证无外部 API Key 时也能运行；配置 OpenAI 兼容接口后，可使用大模型增强场景摘要、人物提取和对白润色。

## 功能

- 自动识别 `第 1 章`、`Chapter 1`、Markdown 标题等章节边界。
- 要求至少 3 个章节输入，避免把短片段误当作完整改编任务。
- 将小说段落拆解为幕、场景、动作、对白和转场说明。
- 输出可编辑 YAML，并提供 JSON Schema 校验。
- 生成 `adaptation_report`，汇总章节覆盖、场景映射、结构指标、质量风险和修订清单。
- 支持 CLI 批处理，适合持续迭代剧本初稿。

## 安装

```powershell
python -m pip install -e .[dev]
```

## 使用

```powershell
python -m novel2script.cli examples/three_chapters.txt --output outputs/fog-city.yaml
```

也可以直接验证输出是否符合 Schema：

```powershell
python -m novel2script.cli examples/three_chapters.txt --output outputs/fog-city.yaml --validate
```

## 可选 AI 增强

设置环境变量后启用 OpenAI 兼容模型：

```powershell
$env:OPENAI_API_KEY="sk-..."
python -m novel2script.cli examples/three_chapters.txt --provider openai --model gpt-4.1-mini
```

如果没有配置 Key，工具会自动回退到本地启发式引擎。

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
- [JSON Schema 文件](schemas/script.schema.json)
