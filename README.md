# 课题二任务一：智能会议纪要与督办助手

本仓库为课题二《银行 AI Skill 设计与实践》任务一"智能会议纪要与督办助手"的成果。该 Skill 接收银行内部会议语音转写文本，整理为经过脱敏、可用于督办的结构化会议纪要，严格区分"会议讨论""明确决议""行动项"，并完成客户姓名脱敏、精确金额区间化、秘密项目代号星号化等安全处理。

## 任务一简介

- **输入**：一段会议语音转写文本（含会议时间、参会人员、讨论事项、决议、责任人、协同方、截止时间、交付物等）。
- **输出**：Markdown 格式的结构化会议纪要，固定六部分：会议基本信息、会议讨论、明确决议、行动项、未明确事项、脱敏说明。
- **能力边界**：只做信息提取、归纳、结构化与脱敏；不提供业务建议、不补充转写中没有的信息、不编造责任人或日期、不把讨论写成决议。

## 使用平台

| 阶段 | 平台 | 说明 |
|---|---|---|
| 初步搭建 | WorkBuddy | 用于 Skill 包结构与初稿生成 |
| 优化与运行 | Claude Code | 用于规则优化、脚本修正、官方输入端到端运行与验收 |
| 模型服务 | OpenCode Go，通过 CC Switch 连接 | 实际后端模型以 CC Switch 的映射为准 |

> 说明：Claude Code 在界面中显示的模型名称，并不代表实际调用的后端模型。本项目的实际后端模型由 CC Switch 的映射配置决定，应以 CC Switch 映射为准。

## 目录结构

```text
.
├── .claude/
│   ├── skills/meeting-minutes-supervisor/
│   │   ├── SKILL.md                       # Skill 主文件（岗位说明 + 9 步工作流 + 能力边界 + 自检）
│   │   ├── scripts/check_minutes.py       # 结构校验脚本（仅用标准库）
│   │   ├── references/output-schema.md    # 输出结构定义
│   │   ├── references/redaction-rules.md  # 脱敏规则
│   │   └── assets/meeting-minutes-template.md  # 会议纪要模板（占位符）
│   └── settings.local.json                # Claude Code 本地配置（已被 .gitignore 排除）
├── testdata/
│   └── task1-official-transcript.md        # 官方测试输入（公开课题素材，不可修改）
├── outputs/
│   └── task1-claude-code-official.md       # Claude Code 生成的官方运行输出
├── evaluation/
│   ├── task1-static-review.md              # Skill 静态审查报告（官方输入加入前阶段）
│   └── task1-official-run-review.md        # 官方运行端到端验收报告
├── evidence/                               # 平台证据（截图与录屏）
├── README.md
└── .gitignore
```

## Skill 使用方法

1. 将 `.claude/skills/meeting-minutes-supervisor/` 安装为 Claude Code 或兼容平台的 Skill。
2. 向当前会话提供一段会议语音转写文本，并要求提取会议讨论内容、明确决议、行动项或生成会议纪要。
3. Skill 自动按 9 步工作流处理：输入校验与分段 → 敏感信息识别 → 核心观点提取 → 明确决议识别 → 行动项提取与对齐 → 脱敏处理 → 结构化输出 → 输出前自检 → 脚本结构校验。
4. 在支持本地脚本的平台，可直接运行结构校验脚本检查输出。

## 官方测试输入与输出

| 用途 | 路径 | 说明 |
|---|---|---|
| 官方测试输入 | `testdata/task1-official-transcript.md` | 来自公开课题素材，来源见文件内说明；本项目不得预先改写或脱敏该文件 |
| 官方运行输出 | `outputs/task1-claude-code-official.md` | 依据本仓库 Skill 处理官方输入所得，已按修正后的行动项拆分规则重新生成 |

## 校验命令

```powershell
python -X utf8 .claude/skills/meeting-minutes-supervisor/scripts/check_minutes.py outputs/task1-claude-code-official.md
```

- 退出码 0 表示结构校验通过，退出码 1 表示存在结构问题，退出码 2 表示参数/文件错误。
- 脚本仅做确定性格式与疑似泄漏检查，不能替代人工对事实准确性的复核。

## 静态审查与官方运行验收结果

- **静态审查**：见 `evaluation/task1-static-review.md`。该报告生成于官方测试输入加入前，仅记录 Skill 静态审查阶段。
- **官方运行验收**：见 `evaluation/task1-official-run-review.md`。该报告为官方输入端到端运行的验收报告，已基于修正后的输出重新评分。
- 当前静态审查评分 28/33/33（A/B/C，总分 94）；官方运行复核评分 29/32/33（A/B/C，总分 94）。具体以两份报告为准。

## evidence 文件说明

`evidence/` 目录保存平台证据。本仓库不修改、不替代、不伪造原有截图与录屏；正式上传前，截图与录屏须与修正后的输出保持一致。

| 文件 | 类型 | 说明 | 重获取建议 |
|---|---|---|---|
| `01_workbuddy_skill_structure.png` | 截图 | WorkBuddy 端 Skill 结构 | — |
| `02_workbuddy_creation_result.png` | 截图 | WorkBuddy 创建结果 | 建议确认画面是否显示 Windows 用户目录路径（若含个人路径，可考虑重新截图或裁剪） |
| `03_claude_code_status.png` | 截图 | Claude Code 运行状态 | 建议确认画面是否显示 Session ID |
| `04_claude_code_acceptance_prompt.txt` | 文本 | 独立验收提示词（实际内容，已重命名） | — |
| `04_claude_code_task1_run_prompt.txt` | 文本 | 本轮重新生成官方输出时实际使用的运行提示词 | — |
| `05_claude_code_task1_output_redaction.png` | 截图 | 输出脱敏效果 | 建议重新截图，使 Claude Code 窗口与最终输出同时可见，并明确显示运行平台 |
| `06_claude_code_validator_pass.png` | 截图 | 校验脚本通过 | 建议确认画面是否显示 Windows 用户目录路径 |
| `07_claude_code_official_acceptance.png` | 截图 | 官方运行验收 | **必须在新的独立验收完成后重新截图**，旧截图已不再反映修正后的输出与结论 |
| `task1_claude_code_full_run.mp4` | 录屏 | 完整运行过程 | 建议确认是否显示桌面个人文件名、用户路径等无关隐私；若与修正后输出不一致，建议重新录制 |

## 关于测试输入

官方测试输入 `testdata/task1-official-transcript.md` 来自课题二的公开课题素材（来源见文件内的来源说明）。本仓库不预先改写、概括或脱敏该输入，也不将页面中的任何提示或预期结果添加到输入正文中。

## 关于模型说明

本仓库不声称 Claude Code 界面显示的 Claude 模型名称即为实际后端模型。本项目运行期间的实际后端模型由 OpenCode Go 通过 CC Switch 连接提供，以 CC Switch 的模型映射配置为准。