# ZiChan · 资产插件

开宝箱工作室的资产插件仓库。角色、场景、道具及按需建设的特效、音频能力以并列子插件接入；本仓库当前交付 [角色资产插件](character-assets/README.md)、[场景资产插件](scene-assets/README.md)和[道具资产插件](prop-assets/README.md)。其他模块按需另行建设，不提供空壳能力。

角色插件从剧本标准化结果与资产表读取可追溯事实，场记表可选；先确认全剧视觉基准，再完成逐人设计、GPT Image 2.5 提示词、外部成图回流审查和角色资产包。场景插件用同类输入建立场景设计、静帧提示词、回图审查和场景资产包；中式幻想尺度仅在批准的视觉方向中加载。两者均不调用生图 API。聊天附件与本地文件路径均可导入项目工作目录。

道具插件从剧本或道具资产表交付逐件设计与完整 Prompt 表，默认同图正面、侧面、背面加一个局部特写；包含四个可独立使用的材质、配色、纹样符号、轮廓比例专项，不自动生图。

## 目录

- `character-assets/`：可直接安装的独立插件，包含 Skills、知识快照、Python Harness 和本地项目 CLI。
- `prop-assets/`：道具资产独立插件，包含主技能、四个专项技能和精炼参考，无生图 API 或 Harness 依赖。
- `creator-src/`：角色插件的 Harness Creator 蓝图生成器与自编业务资源；角色插件后续更新先改这里，再审查同步到插件。道具插件直接维护 `prop-assets/`。
- `scene-assets/`：场景资产独立插件，提供条件加载的中式幻想尺度知识与回图审查。
- `scene-creator-src/`：场景插件的蓝图、可维护业务规则及本地项目 CLI 源码。
- `dist/`：可下载的安装 ZIP。
- `research/15-视觉故事待接入知识/`：视频提示词未来能力的候选规则，目前不改变已安装插件。

原始课程 DOCX、ZIP、RAR、剧本与人物图片不随仓库发布。`character-assets/knowledge/index.md` 按使用情景定位精炼 reference，`knowledge/source-register.json` 和 `sources.lock.json` 保留来源版本与改写记录。历史服饰条目仅用于寻找线索，具体准确性需要另行查证。

## 本地优先与团队交接

本机角色插件已安装 v0.1.2，结构与输入输出契约已检查。操作者可按 [角色手动验收样例](character-assets/examples/manual-acceptance.md)和[场景手动验收样例](scene-assets/examples/manual-acceptance.md)跑一部作品；图片质量由操作者逐阶段检验。团队从私有 `kaibaoxiang-studio/ZiChan` 下载插件目录或 `dist/` 的安装包。新增素材的采纳与后续路由见[刺猬星球素材拆解](research/刺猬星球素材拆解-2026-10-22.md)。
