# 工作流与项目状态

主控先接收标准剧本、资产表和可选场记，使用 `scripts/scene_project.py init` 建立本地项目。随后依次提交视觉基准、场景设计卡、静帧提示词、外部回流图和审查 JSON；每个批准动作记录操作者、UTC 时间与对象 SHA。

CLI 入口：`init --project-root DIR --project-id ID --screenplay FILE --asset-table FILE [--scene-log FILE]`；`submit --project-root DIR --kind visual-bible|design|prompt|review --file FILE [--scene-id ID --variant-id ID --image-id ID]`；`approve-record --project-root DIR --kind visual-bible|design --operator NAME [--scene-id ID --variant-id ID]`；`add-image --project-root DIR --scene-id ID --variant-id ID --file FILE`；`approve-image --project-root DIR --scene-id ID --variant-id ID --image-id ID --operator NAME`；`refresh --project-root DIR [--screenplay FILE --asset-table FILE --scene-log FILE]`；`package --project-root DIR --scene-id ID --variant-id ID --output DIR`；`status --project-root DIR`。命令逐步检查当前来源和批准依赖；失败时保留旧文件和错误说明。

首版 `refresh` 对任一输入 SHA 变化撤销所有记录与图片审批；操作者核对影响后重新提交并批准。场景级自动差异分析与完整图生视频工作流留待后续版本。
