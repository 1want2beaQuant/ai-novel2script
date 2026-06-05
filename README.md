# AI 小说转剧本工具

面向小说作者的 AI 辅助改编工具，可将 3 个章节以上的小说文本转换为结构化剧本 YAML 初稿。工具默认使用本地启发式改编引擎，保证无外部 API Key 时也能运行；配置 OpenAI 兼容接口后，可使用大模型增强场景摘要、人物提取和对白润色。

## 功能

- 自动识别 `第 1 章`、`第一章`、`序章`、`尾声`、`Chapter One`、`Chapter IV`、`Ch. 3`、Markdown 标题等章节边界。
- 要求至少 3 个章节输入，避免把短片段误当作完整改编任务。
- 将小说段落拆解为幕、场景、动作、对白和转场说明。
- 输出可编辑 YAML，并提供 JSON Schema 校验。
- 生成 `structure_map`，把开场、诱发事件、中点、高潮和结局映射到具体场景。
- 生成 `story_bible`，整理人物连续性、地点、道具/线索和待解问题。
- 生成 `adaptation_report`，汇总章节覆盖、场景映射、结构指标、质量风险和修订清单。
- 生成 `coverage_report`，按专业 coverage 思路给出推荐等级、分项评分、强弱项和优先修订动作。
- 支持 Fountain 剧本文本导出，便于进入专业剧本编辑器继续打磨。
- 支持 CLI 批处理，适合持续迭代剧本初稿。
- 提供本地 Web 工作台，可在浏览器中导入手稿、预检章节识别、转换 YAML/Fountain、查看 coverage 诊断、结构节拍、场景索引和修订动作，并下载结果。

## 安装

本地开发：

```powershell
python -m pip install -e ".[dev]"
```

需要 OpenAI 兼容模型增强时安装可选依赖：

```powershell
python -m pip install -e ".[dev,ai]"
```

未来发布包可用后，也可以直接安装：

```powershell
python -m pip install novel2script
```

安装后可直接使用 CLI 或模块入口：

```powershell
novel2script --version
python -m novel2script --version
novel2script path\to\novel.txt --output outputs\script.yaml --validate
```

## 使用

```powershell
novel2script path\to\novel.txt --output outputs\script.yaml
```

也可以直接验证输出是否符合 Schema：

```powershell
novel2script path\to\novel.txt --output outputs\script.yaml --validate
```

需要导出剧本文本时，可以选择 Fountain：

```powershell
novel2script path\to\novel.txt --format fountain --output outputs\script.fountain
```

如果当前 shell 找不到 console script，也可以使用模块入口：

```powershell
python -m novel2script path\to\novel.txt --output outputs\script.yaml --validate
```

克隆仓库后，可以直接用内置示例试运行：

```powershell
python -m novel2script examples\three_chapters.txt --output outputs\fog-city.yaml --validate
python -m novel2script examples\three_chapters.txt --format fountain --output outputs\fog-city.fountain
```

## 本地 Web 工作台

启动浏览器界面：

```powershell
novel2script-web --host 127.0.0.1 --port 8765
```

如果当前 shell 找不到 console script，也可以使用模块入口：

```powershell
python -m novel2script.web --host 127.0.0.1 --port 8765 --no-open
```

打开 `http://127.0.0.1:8765` 后，可以导入 `.txt` 手稿、选择 YAML 或 Fountain 输出、切换本地或 OpenAI 模式。页面会用本地后端预检章节识别结果，并在转换后展示章节覆盖率、coverage 分项评分、结构节拍、优先修订动作、风险提示和场景索引。默认本地模式不会把手稿发送到外部服务；选择 OpenAI 且配置 `OPENAI_API_KEY` 后，行为与 CLI 的 `--provider openai` 相同。

Web 工作台默认只绑定本机 loopback 地址。若确实需要让局域网内其他设备访问，必须同时传入非本机 `--host` 和 `--allow-remote`；这样会把页面和手稿转换 API 暴露给该网络，请只在受信任网络中使用。
预检和转换 API 只接受 JSON 请求；浏览器请求携带 `Origin` 时必须与当前 Web 工作台同源。

## 可选 AI 增强

设置环境变量后启用 OpenAI 兼容模型：

```powershell
$env:OPENAI_API_KEY="sk-..."
novel2script path\to\novel.txt --provider openai --model gpt-4.1-mini
```

如果没有配置 Key，工具会自动回退到本地启发式引擎。

默认本地模式不会调用外部 AI 服务。启用 `--provider openai` 且设置 `OPENAI_API_KEY`
后，工具会把截断后的章节摘要和本地生成的 baseline JSON 发送给 OpenAI 兼容接口；
返回内容会按 JSON 对象解析（支持常见 fenced JSON 代码块），并在替换本地草稿前通过内置 Schema 校验。
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

- CI 在 PR 和 `main` push 上运行 Python 3.10-3.14 测试、ruff、CLI smoke test、Schema 同步检查、包构建检查、Windows smoke 和依赖安全审计。
- 发布 workflow 监听 `v*.*.*` 标签，校验标签版本、构建 wheel/sdist、安装 wheel/sdist 做 smoke test，并通过 PyPI Trusted Publishing 发布；PyPI 发布成功后创建 GitHub Release。
- Dependabot 每周检查 Python 依赖和 GitHub Actions 更新。
- 项目当前优先完善核心功能与前端界面；首次发布前请先在 PyPI 创建 `novel2script` 的 pending publisher，并绑定 GitHub `pypi` environment。
