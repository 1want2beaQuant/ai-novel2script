# 发布检查清单

本文档用于把 `novel2script` 从可运行项目推进到可发布、可维护的 Python 包。

## 发布前

1. 确认 `main` 分支 CI 全绿。
2. 更新 `pyproject.toml` 中的 `version`。
3. 如本次发布调整了 AI provider、远程请求 payload、输出文件或 API Key 处理方式，同步更新 `PRIVACY.md`。
4. 本地执行：

```powershell
python -m pip install -e .[dev,release,security]
python -m pytest
python -m ruff check .
python -m pip_audit --skip-editable
python scripts\check_release_tag.py v0.1.0
python -m build
python -m twine check dist\*
novel2script --version
python -m novel2script --version
python -m novel2script.cli examples/three_chapters.txt --output outputs/release-smoke.yaml --validate
python -m novel2script.cli examples/three_chapters.txt --format fountain --output outputs/release-smoke.fountain
cmd /c fc /b schemas\script.schema.json src\novel2script\schemas\script.schema.json
```

5. 在 PyPI 项目中配置 Trusted Publishing：
   - Owner：`1want2beaQuant`
   - Repository：`ai-novel2script`
   - Workflow：`release.yml`
   - Environment：`pypi`

## 发布

创建并推送与 `pyproject.toml` 版本一致的语义化版本标签：

```powershell
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions 会校验标签与包版本一致、构建 wheel/sdist、在干净虚拟环境中分别安装
wheel 和 sdist 并运行 CLI smoke test，然后通过 PyPI Trusted Publishing 发布。PyPI 发布成功后，
workflow 会创建包含 wheel/sdist 资产的 GitHub Release。

## 发布后

1. 在干净虚拟环境中安装发布包。
2. 运行 `novel2script --version`、`python -m novel2script --version`、`novel2script --help` 和示例转换命令。
3. 核对 PyPI 页面中的 README、许可证、项目链接和版本号。
4. 核对 GitHub Release 页面中的 release notes、wheel 和 sdist 资产。
