# 角色资产插件 v0.1.0

独立安装的 Codex 插件。主入口为 `$character-assets`；辅助入口：`$character-evidence`、`$character-design`、`$character-image-prompt`、`$character-image-review`、`$character-image-edit`。它们是可单独调用的 Skills，默认由主入口按当前阶段选择，不要求同时启动多个 Agent。

## 输入与产物

标准化剧本和资产表必需，场记表可选。支持 JSON、Markdown、Excel，优先使用 JSON；也可用顶层 `AssetProjectSnapshotV1` 初始化。文件可以作为聊天附件提供，也可以给绝对路径。项目工作目录保留原件副本、SHA、设计卡、提示词、回流图片、审查与审批。最终 `CharacterAssetPackV1` 只包含对应角色变体的已定稿材料。

插件**只写 GPT Image 2.5 提示词**。操作者在外部工具生成图片，回传并逐阶段确认。人形执行资产表上左正脸、上右约 45° 半侧脸；下左是从颈肩以下到鞋的放大无头正面服装主体，下右是从头到鞋的完整背面。非人按设计卡批准的版式适配。

## 安装

保留整个插件目录，使用 Python 3.12+：

```sh
python3 scripts/bootstrap.py --install
python3 harness.py doctor
codex plugin marketplace add /absolute/path/to/character-assets --json
codex plugin add character-assets@zichan-local --json
```

安装后在新聊天选择“角色资产插件”，或输入 `$character-assets`。如果当前聊天尚未刷新已安装 Skill 清单，请开新聊天。插件目录内不放剧本或回流图；让主入口在工作区创建项目目录。

## 首次使用

```text
$character-assets 请用这份标准化剧本和资产表建立角色资产项目；场记表也在附件中。
先给出第 -1 阶段视觉基准与全员轻规划，再从 CHR-001 开始分轮设计。
```

主入口会按 [工作流](references/workflow.md) 使用 `scripts/character_project.py`。想单独审查已有图，可调用 `$character-image-review` 并给出项目目录和图片。需要局部修图提示词，可调用 `$character-image-edit`。结构化 JSON 格式见 [接口](references/interfaces.md)；知识按 [索引](knowledge/index.md) 加载。

本地 CLI 可直接查看项目：

```sh
python3 scripts/character_project.py status --project-root /absolute/project/directory
```

手动测试材料见 [样例剧本、资产表与验收清单](examples/manual-acceptance.md)。

原始课程、外部 RAR、剧本和具体人物参考图都不在插件内；本包只有独立改写的规则与来源收据。图片审查依赖实际回流图片，结构验证不等同于视觉验收。
