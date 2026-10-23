# 场景资产插件 v0.1.0

本目录以 `sence-prompts` 替换原场景资产实现；插件名称仍为 `scene-assets`，内置技能入口为 [`$sence-prompts`](skills/sence-prompts/SKILL.md)。版本号按本次发布要求统一为 `0.1.0`，不是原同版本 Harness 实现的兼容升级，具体内容以 Git 提交区分。

支持根据完整资产表及剧本设计中文静态场景提示词，第二步光影氛围与本地色卡，第三步反打／其他角度，以及局部修改和纹理修复。不提取资产、不生成视频分镜、不自动调用场景出图服务。

## 使用与安装

仓库根目录现已提供本地市场入口，可在完整 checkout 根目录直接安装：

```sh
codex plugin marketplace add "$PWD"
codex plugin add scene-assets@scene-assets-local
codex plugin list
```

添加市场会记录其来源，安装会写入 Codex 插件配置和缓存；若已有同名市场先核对来源，不自动覆盖。保留注册的本地目录。原个人 `sence-prompts` skill 不必删除；如选择器出现同名条目，选择场景资产插件下的技能。

插件安装保留完整 `scene-assets/`。使用仓库 [本地市场安装包](../dist/scene-assets-local-marketplace.zip)时，解压后沿用现有安装方式：

```sh
codex plugin marketplace add /absolute/path/to/scene-assets-local-marketplace
codex plugin add scene-assets@scene-assets-local
```

仅安装 Skill 时，将整个 `skills/sence-prompts/` 目录复制到个人技能目录，不只复制 SKILL.md；也可下载 [插件目录压缩包](../dist/scene-assets-0.1.0.zip)。本包提供提示词，操作者在外部生成场景图；第二步色卡绘制需要 Python 与 Pillow，并有可用中文字体。

```text
$sence-prompts 根据这份完整资产表与对应剧本，为指定场景生成一条完整中文静态场景提示词。
```

已有可靠图／完整文字稿时可直接进入打光、反打或局部修改，不必重交全表；依赖原图的编辑任务仍须提供实际可访问图像。验证方法见 [验证规则](skills/sence-prompts/references/verification.md)。文件与文字检查不代表真实出图、像素保留或空间实测通过。

## 构建与验证

仓库根目录运行：

```sh
python3 -B scene-plugin-maintenance/package_plugin.py
./scene-plugin-maintenance/init.sh
```

构建只替换 `dist/` 中两个场景 ZIP；维护 harness 不进入安装包。版本按用户要求保持 `0.1.0`，构建内容以 Git 提交及 ZIP SHA256 区分。
2026-10-23：26 项单元测试通过；260 个技能文件、205 本地链接及 52 锚点通过；本地 CLI 安装显示 installed, enabled，安装缓存与源一致。新会话实际调用及真实场景出图尚未验证。
详细边界见 [维护说明](../scene-plugin-maintenance/README.md)。

## 替换边界

原 `scene-assets`、`scene-design`、`scene-evidence`、`scene-image-prompt`、`scene-image-review` 五个技能及其 Harness／项目 CLI 已从当前插件移除，不再运行旧 bootstrap 或 harness.py；旧项目审批、设计卡和数据接口不会自动迁移。

旧实现保留在 Git 历史与替换前备份。仓库 `scene-creator-src/` 保留历史源码，不是当前插件的生成来源；当前技能直接维护 `scene-assets/skills/sence-prompts/`。本次两个同名 ZIP 已重新打包为当前实现，历史安装包可从此前 Git 提交恢复。之前的 `feat/sence-prompts` 分支保留原上传版本，不作为当前 main 的发布入口。
