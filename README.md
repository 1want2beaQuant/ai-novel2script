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
- 每场输出戏剧目标、冲突和转折，便于从“章节摘要”继续改成真正可演的场景。
- 支持 Fountain 剧本文本导出，便于进入专业剧本编辑器继续打磨。
- 支持 Markdown 修订简报导出，汇总 coverage 结论、分项评分、优先修订动作、结构节拍和场景索引。
- 支持 CLI 批处理，适合持续迭代剧本初稿。
- 提供本地 Web 工作台，可在浏览器中导入手稿、预检章节识别和每章素材规模、转换并切换查看
  YAML/Fountain/Markdown 修订简报/draft JSON/summary JSON、查看 coverage 诊断、下一轮修订重点、结构节拍、场景索引、场景目标/冲突/转折、场景块预览和修订动作，
  从导出清单直接查看或下载单个文件、打包下载全部导出文件，并清空当前工作台状态。

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

输入文件需要是 UTF-8 文本。

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

需要导出可直接发给作者或协作者的修订简报时，可以选择 Markdown：

```powershell
novel2script path\to\novel.txt --format markdown --output outputs\revision.md
```

如果当前 shell 找不到 console script，也可以使用模块入口：

```powershell
python -m novel2script path\to\novel.txt --output outputs\script.yaml --validate
```

克隆仓库后，可以直接用内置示例试运行：

```powershell
python -m novel2script examples\three_chapters.txt --output outputs\fog-city.yaml --validate
python -m novel2script examples\three_chapters.txt --format fountain --output outputs\fog-city.fountain
python -m novel2script examples\three_chapters.txt --format markdown --output outputs\fog-city.revision.md
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

打开 `http://127.0.0.1:8765` 后，可以导入 `.txt` 手稿、选择初始 YAML、Fountain 或 Markdown 修订简报结果视图、切换本地或 OpenAI 模式。页面会用本地后端预检章节识别结果，显示每章字数，并标记正文偏短的章节，方便在转换前补齐素材；短章提示不会阻止满足 3 章要求的手稿继续转换。转换后页面会展示章节覆盖率、章节到场景映射、coverage 分项评分、下一轮修订重点、结构节拍、优先修订动作、人物连续性、地点资产、道具/线索、待解问题、风险提示、实际处理方式和场景索引；下一轮修订重点会聚合优先级、分项分数和评分理由，方便先处理最影响改编质量的问题；场景索引会覆盖全部生成场景，直接显示每场的戏剧目标、冲突、转折、剧本块统计和动作/对白/旁白/转场预览，并可按人物、地点、目标、冲突、转折或块预览文本筛选。结果区可在 YAML、Fountain、Markdown 修订简报、Draft JSON 和 Summary JSON 之间切换，不需要重新转换；导出清单会显示当前可下载文件、扩展名、字节大小和打包总量，并可直接查看或下载任一导出文件；复制和顶部单文件下载会使用当前结果视图，打包下载会生成包含全部导出文件的 zip。工作台会自动保存当前手稿、片名、输出格式、处理模式、模型和 Schema 开关到本机浏览器，并在刷新页面后自动恢复；生成结果和远程确认状态不会随刷新恢复。清空按钮会移除当前手稿、标题、生成结果、诊断状态、选中文件引用、远程确认状态和浏览器本地保存的草稿；已下载的文件或已复制到其他位置的内容需要自行管理。顶部状态会显示当前后端版本，`/api/health` 会返回版本、默认模型和 Web 请求上限，便于排查运行环境。默认本地模式不会把手稿发送到外部服务；选择 OpenAI 且配置 `OPENAI_API_KEY` 后，行为与 CLI 的 `--provider openai` 相同，Web 页面会在开始远程转换前按当前手稿、片名和模型要求确认。

Web 工作台默认只绑定本机 loopback 地址。若确实需要让局域网内其他设备访问，必须同时传入非本机 `--host` 和 `--allow-remote`；这样会把页面和手稿转换 API 暴露给该网络，请只在受信任网络中使用。
预检和转换 API 只接受 JSON 请求；浏览器请求携带 `Origin` 时必须与当前 Web 工作台同源。单次 Web 请求上限为 2 MB，超大手稿请拆分后再导入、预检或转换。

## 可选 AI 增强

设置环境变量后启用 OpenAI 兼容模型：

```powershell
$env:OPENAI_API_KEY="sk-..."
novel2script path\to\novel.txt --provider openai --model gpt-4.1-mini
```

如果没有配置 Key，工具会自动回退到本地启发式引擎。CLI 会输出 warning，Web 工作台会在处理模式卡片显示“本地回退”，方便确认实际没有远程增强。

默认本地模式不会调用外部 AI 服务。启用 `--provider openai` 且设置 `OPENAI_API_KEY`
后，工具会把截断后的章节摘要和本地生成的 baseline JSON 发送给 OpenAI 兼容接口；
远程增强提示会要求保留 baseline JSON 的完整字段结构，并可补强场景目标、冲突、转折、
摘要、节拍和剧本块文本；
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

- CI 在 PR 和 `main` push 上运行 Python 3.10-3.14 测试、ruff、YAML/Fountain/Markdown CLI smoke test、Schema 同步检查、包构建检查、Windows smoke 和依赖安全审计。
- 发布 workflow 监听 `v*.*.*` 标签，校验标签版本、构建 wheel/sdist、安装 wheel/sdist 做 smoke test，并通过 PyPI Trusted Publishing 发布；PyPI 发布成功后创建 GitHub Release。
- Dependabot 每周检查 Python 依赖和 GitHub Actions 更新。
- 项目当前优先完善核心功能与前端界面；首次发布前请先在 PyPI 创建 `novel2script` 的 pending publisher，并绑定 GitHub `pypi` environment。
