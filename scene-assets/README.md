# 场景资产插件 v0.1.0

独立的 `$scene-assets` 插件：依据标准剧本、资产表和可选场记，建立可追溯的场景设计卡，编写外部出图提示词，并审查回流图。`$scene-evidence`、`$scene-design`、`$scene-image-prompt`、`$scene-image-review` 可单独使用。插件不调用生图或视频 API。

中式幻想尺度方法是**按项目批准才加载**的知识情景。普通现实场景不自动加入仙宫、女性仙人或超现实空间。源方法缺少许可证，包内只有独立改写的规则和文件哈希收据，不包含原 Skill、示例提示词或图片。

## 本地使用

保留完整目录，用 Python 3.12+ 运行 `python3 scripts/bootstrap.py --install` 和 `python3 harness.py doctor`。从仓库的 `dist/scene-assets-local-marketplace.zip` 解压本地市场后，执行 `codex plugin marketplace add /absolute/path/to/scene-assets-local-marketplace`、`codex plugin add scene-assets@scene-assets-local`。安装后选择“场景资产插件”或明确调用 `$scene-assets`。聊天附件或本地路径均可作为输入；结构化接口见 [接口说明](references/interfaces.md)。

```text
$scene-assets 依据这份标准剧本和资产表建立场景项目。先列场景原文事实与疑点，再给出全剧视觉基准和场景设计卡；在我确认后写外部出图提示词。
```

若剧本已经批准中式幻想视觉方向，可追加“为 SCN-001 使用中式幻想尺度知识”；未批准时先提出选择，不能直接写成项目事实。操作者外部出图后用 `$scene-image-review` 回传并审查。小型项目状态 CLI 的命令见 [工作流](references/workflow.md)；手动验收路径见 [样例](examples/manual-acceptance.md)。

## 已知边界

首版只处理场景静帧资产。场景内部人物由已批准角色资产提供身份参考，不在这里重新设计角色；首尾帧视频提示词留给后续能力。输入改版会保守地使当前审批全部失效，由操作者核对并重新提交；尚未提供自动场景级差异判定。
