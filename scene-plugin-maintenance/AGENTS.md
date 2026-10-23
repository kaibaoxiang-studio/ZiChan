# 场景插件维护 Harness

## Startup Workflow

先读本目录 README.md、feature_list.json、progress.md 和 session-handoff.md，再从仓库根目录运行 `./scene-plugin-maintenance/init.sh`。
这些文件只指导插件维护，不是场景生成时的必读规则。

## Scope / Working Rules

- 当前目标：将已有 sence-prompts 打包为 Codex scene-assets 插件，保持版本 0.1.0。
- One feature at a time：维护一个明确功能，保留无关用户修改。
- 本文路径除状态文件外均以仓库根目录为基准；技能源码为 scene-assets/skills/sence-prompts/；不恢复旧 runtime / 五技能实现。
- 构建只替换 dist/ 中两个具名 ZIP，不修改安装配置、不联网、不生成场景图。
- 修改技能后按技能自带 tests/index.md 选测；不要把插件维护规则写入技能。
- 安装、提交和上传需对应的用户授权；不要依照本文件自动推送 GitHub。

## Verification / Definition of Done

`./scene-plugin-maintenance/init.sh` 检查插件身份、版本、市场路径、ZIP 内容、打包测试和技能文件链接。
构建：`python3 -B scene-plugin-maintenance/package_plugin.py`，然后再次运行验证。
“已安装”必须有 Codex 安装结果及列表证据；文件检查不证明生成质量或新会话调用通过。

## End of Session

更新 feature_list.json、progress.md、session-handoff.md 中的状态、evidence、风险和下一步。
保留可重启的构建目录；失败时记录阻塞及已尝试方法，不写虚假的完成状态。
