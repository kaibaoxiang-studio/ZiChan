# Session Handoff

## Current Objective

场景插件 scene-assets 0.1.0 提供 sence-prompts；维护 harness 位于插件外。

## Files Changed

新增根目录 .agents/plugins/marketplace.json 与 scene-plugin-maintenance/；更新场景安装说明、根 README 和两个安装 ZIP。未改角色／道具插件与场景技能规则。

## Verification Evidence

26 项测试通过；205 链接与 52 锚点通过；技能缓存 260 文件与源一致；插件清单 263 文件、市场包 264 文件。新会话与真实出图未测试。

## Blockers / Risks

CLI 安装不等于本会话热加载成功；保留同名个人 skill。版本按用户指定保持 0.1.0，相同版本不同构建需以 Git 提交与 ZIP SHA256 区分。

## Next Session Startup

读 AGENTS.md、feature_list.json、progress.md，再从仓库根目录运行 ./scene-plugin-maintenance/init.sh。
后续发布需对应用户授权；构建统一使用本目录 package_plugin.py，不运行旧场景生成器。
