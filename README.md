# ZiChan · 资产插件

开宝箱工作室的资产插件仓库。角色、场景、道具及按需建设的特效、音频能力以并列子插件接入；本仓库当前交付可独立安装的 [角色资产插件](character-assets/README.md)。其他分支由团队成员另行建设，不在本次角色插件内提供空壳能力。

角色插件从剧本标准化结果与资产表读取可追溯事实，场记表可选；先确认全剧视觉基准，再完成逐人设计、GPT Image 2.5 提示词、外部成图回流审查和角色资产包。插件不调用生图 API。聊天附件与本地文件路径均可导入项目工作目录。

## 目录

- `character-assets/`：可直接安装的独立插件，包含 Skills、知识快照、Python Harness 和本地项目 CLI。
- `creator-src/`：Harness Creator 蓝图生成器与自编业务资源；后续更新先改这里，再审查同步到插件。
- `dist/`：可下载的安装 ZIP。

原始课程 DOCX、ZIP、RAR、剧本与人物图片不随仓库发布。`character-assets/knowledge/index.md` 按使用情景定位精炼 reference，`knowledge/source-register.json` 和 `sources.lock.json` 保留来源版本与改写记录。历史服饰条目仅用于寻找线索，具体准确性需要另行查证。

## 本地优先与团队交接

本机已安装 v0.1.1，结构与输入输出契约已检查。操作者可按 [手动验收样例](character-assets/examples/manual-acceptance.md) 跑一部作品；图片生成、中文标签和四格执行表的视觉质量由操作者逐阶段检验。团队从私有 `kaibaoxiang-studio/ZiChan` 下载 `character-assets/` 或 `dist/` 的安装包。新增素材的采纳与后续路由见[刺猬星球素材拆解](research/刺猬星球素材拆解-2026-10-22.md)。
