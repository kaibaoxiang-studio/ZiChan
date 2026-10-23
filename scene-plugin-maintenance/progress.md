# Progress

## 2026-10-23

- 完成：本地插件安装、可复现打包脚本、市场入口与维护 harness；技能规则未修改。
- Verification evidence：6 项打包测试与 20 项技能文件测试通过；260 个技能文件、205 本地链接、52 锚点无错误。插件 ZIP 263 文件、市场 ZIP 264 文件。
- 本机安装：scene-assets@scene-assets-local / 0.1.0 显示 installed, enabled；安装缓存与源一致。这是一次机器本地记录，不是团队默认安装状态。
- 发布目标：用户已授权更新 main；仅场景插件、维护与安装入口，不改角色／道具插件。
- Risks：原个人 skill 与插件技能同名，未删除原 skill；新会话实际调用和真实出图未验证。
- Next step：新会话选中场景资产插件的 sence-prompts 并用实际素材验证。
- Restart：读本目录状态文件，从仓库根目录运行 ./scene-plugin-maintenance/init.sh。
