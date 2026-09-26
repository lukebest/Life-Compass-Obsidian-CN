# Omarchy 集成

把这份库接到 Omarchy 桌面上。笔记仍是唯一的数据。AI 用系统当前的默认 agent（`omarchy default agent`，例如 Cursor CLI），不在配置里写死。

交互式对话仍遵守 [[AGENTS]]：先读，再问，你点头才改。定时和捕获走 Autonomous mode，可以直接追加简报、复盘草稿和任务行。删除、改写已有日记、以及替你填 `dq_*` 仍然不做。每次运行都有快照，`compass undo` 能退回。

## 安装

在库的根目录：

```bash
integrations/omarchy/install.sh
```

脚本会做这些事，并且可以重复运行：

- 把 `compass` 链接到 `~/.local/bin/compass`
- 把状态栏组件链接到 `~/.config/omarchy/plugins/luke.compass`，并加到 `shell.json` 的中间区域
- 在 Hyprland 快捷键和 Omarchy 菜单里追加带 `compass` 标记的一块
- 安装两个用户级 systemd 单元：每 15 分钟的 `compass-tick.timer`（`Persistent=true`，睡眠醒来会补跑），以及前台活动采样服务

卸掉：`integrations/omarchy/install.sh --uninstall`。这不会删除库里的笔记，也不会删除 `~/.local/state/compass/` 里的运行记录。

时间写在 [[Compass Config#自动化（Omarchy）]] 的 `automation.jobs`。计时器只负责每 15 分钟叫醒一次，具体跑哪个任务由 `compass tick` 按配置决定。

## 你怎么用

| 入口 | 作用 |
| --- | --- |
| `Super+Shift+C` | 弹出输入（可以接着用语音输入）。原文先进入 `08 Tasks/Tasks.md` 的 Inbox，再由 agent 路由成任务、日记或项目想法 |
| `Super+Shift+J` | 打开今天的日记 |
| `Super+Alt+A` | 在这份库里打开默认 agent，交互式对话 |
| 状态栏数字 | `到期·逾期`。悬停看今天最多三件事。左键打开 Compass 菜单，右键捕获。暂停时图标变灰 |
| 菜单 Compass | 简报、分拣、周复盘草稿、日志、撤销、暂停、恢复 |

提醒不调用模型：逾期、当天下午 4 点前还没做完的、晚上 8 点还没勾的习惯、理想一周里即将开始的时间块、周日的周复盘。`quiet_hours` 里不响，每天有上限。

## 定时任务

| 任务 | 默认时间 | 写入 |
| --- | --- | --- |
| 晨间简报 | 07:30 | 当日笔记 `## AI 简报` |
| 晚间复盘 | 21:30，错过则次日午前补昨晚 | 当日笔记 `## AI 复盘`，分数只作建议 |
| 收件箱分拣 | 09:00 到 21:00，每 3 小时 | `08 Tasks/Tasks.md` 的任务行 |
| 看板整理 | 18:00 | 项目和写作看板的卡片移动 |
| 周复盘草稿 | 周日 20:00 | 周笔记的两个复盘小节，每条以 `AI 草稿：` 开头 |
| 季度准备 | 季度最后一周 20:00 | `Agent/Reports/`，不改静修笔记 |
| 库健康检查 | 周日 19:00 | `Agent/Reports/` |
| 活动汇总 | 23:50 | 当日笔记 `## 今日活动`，按类别和应用，没有窗口标题 |

提示词在 `Prompts/Auto/`。它们是无头版本，不经过 [[20 Prompt Library]] 里的按钮。

定时任务如果发现当天或当周的笔记还不存在，会写一份骨架：属性、标题，以及简报、复盘、活动这几节。它不会跑 Templater，所以没有仪表盘查询。想要完整模板时，在笔记还不存在的时候用 Obsidian 的周期笔记命令创建。

季度准备和健康检查只写 `Agent/Reports/`，不会为了跑任务去新建季度笔记。

前台活动的原始记录在 `~/.local/state/compass/activity/`，不进库，也不发给模型。汇总进日记的只有类别和应用时长。锁屏一类的窗口在 `activity.exclude` 里。

## 权限

无头的 Cursor CLI 使用 `--force`，所以 [[AGENTS]] 的 Autonomous mode 和两道护栏一起生效：

- 库里的 `.cursor/cli.json` 拒绝改 `.obsidian/`、`Templates/`、`Prompts/`、`Meta/`、`integrations/`，并拒绝 shell
- 运行器在调用 agent 之前对文本文件做快照。日记、静修和计划笔记只允许在末尾追加。已有行被改掉或删掉时，运行器会把文件改回去，并通知你

日志在 `Agent/Log/`。撤销：

```bash
compass undo
compass undo <run-id>
```

如果那个文件在运行之后又被改过，撤销会停下来，不覆盖你后来的修改。

暂停和恢复：

```bash
compass pause
compass resume
```

暂停时状态栏变灰，定时任务和提醒都不跑。`compass status` 仍会刷新到期数字。

## 换默认 agent

`omarchy default agent` 决定用谁。目前无头调用写了 `cursor-agent`、`claude`、`codex` 三种。其他名字会直接退出，不会猜参数。交互式入口始终走 `omarchy agent`，所以菜单和快捷键会跟着系统默认值走。
