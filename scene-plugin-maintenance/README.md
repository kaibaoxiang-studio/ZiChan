# 场景插件构建与维护

本目录由 harness-creator 模板起步，收敛为插件构建、验证和交接流程。它不是场景生成 runtime，也不打入插件安装包。

仓库根目录运行：

```sh
python3 -B scene-plugin-maintenance/package_plugin.py
./scene-plugin-maintenance/init.sh
```

仅需 Python 3.9+ 标准库。脚本不联网、不改 Codex 配置、不修改技能、不生成场景图；只替换 dist/scene-assets-0.1.0.zip 和 dist/scene-assets-local-marketplace.zip 两个生成物。
固定 ZIP 元数据保证相同输入生成相同安装包，验证逐文件字节及文件清单。`--check` 只读，不构建。

技能源码唯一维护在 scene-assets/skills/sence-prompts/。修改规则或依赖后按技能自带 tests/index.md 选测；场景生成质量、新会话调用及像素／空间验证不能由文件测试替代。

scene-creator-src/build.py 是已禁用覆盖的旧实现；旧 build_local_marketplace.py 是历史打包入口，不保证当前可复现构建约定，当前应统一使用本目录脚本。

状态见 feature_list.json、progress.md 和 session-handoff.md。本地机器上的安装记录只作为一次验证证据，不表示每个使用者已经安装。安装说明见 ../scene-assets/README.md。
