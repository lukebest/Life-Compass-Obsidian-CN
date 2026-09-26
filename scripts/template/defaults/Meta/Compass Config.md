---
locale: zh-CN
birthdate:
life_expectancy: 80
daily_folder: 01 Journal/Daily
weekly_folder: 01 Journal/Weekly
quarterly_folder: 01 Journal/Quarterly
retreat_folder: 02 Retreats
projects_folder: 04 Projects
dq_prefix: dq_
habit_prefix: habit_
wheel_prefix: wheel_
board_done_lanes: Done,Published,Archive
questions:
  - key: dq_goals
    text: 今天我是否尽力设定了清晰的目标？
  - key: dq_progress
    text: 今天我是否尽力推进了自己的目标？
  - key: dq_meaning
    text: 今天我是否尽力去发现意义？
  - key: dq_happy
    text: 今天我是否尽力让自己快乐？
  - key: dq_relationships
    text: 今天我是否尽力建立积极的人际关系？
  - key: dq_engaged
    text: 今天我是否尽力全情投入？
habits:
  - habit_journal
  - habit_exercise
  - habit_reading
wheel_areas:
  - wheel_health
  - wheel_relationships
  - wheel_family
  - wheel_career
  - wheel_finances
  - wheel_growth
  - wheel_fun
  - wheel_meaning
automation:
  enabled: true
  vault_path:
  quiet_hours: "23:00-07:00"
  max_nudges_per_day: 8
  task_exclude:
    - 09 Reading/
  jobs:
    morning-brief: "07:30"
    evening-recap: "21:30"
    triage: "every 3h 09:00-21:00"
    board-groom: "18:00"
    weekly-draft: "Sun 20:00"
    quarter-prep: "quarter-last-week 20:00"
    vault-health: "Sun 19:00"
    nudge: "15m"
    activity-rollup: "23:50"
  activity:
    sample_seconds: 30
    exclude: "hyprlock,omarchy-lock,swaylock"
    categories:
      code: "cursor,code,zed,nvim,vim,emacs,alacritty,ghostty,kitty,foot"
      writing: "obsidian"
      browser: "chromium,firefox,brave,chrome"
      comms: "signal,telegram,discord,slack"
---
# 人生罗盘配置

这是系统读取设置的唯一位置。`Meta/views/` 中的每个仪表盘组件都以 `dv.page("Meta/Compass Config")` 开始；创建新笔记时，每日笔记、静修复盘和每日问题模板也会读取下方列表。只需在这里修改，无须移动其他文件。

## 个人设置

| 属性 | 使用位置 | 说明 |
| --- | --- | --- |
| `birthdate` | 生命倒计时组件 | ISO 日期，格式为 `YYYY-MM-DD`。设置前保持为空。 |
| `life_expectancy` | 生命倒计时组件 | 预期寿命，单位为年。 |

## 每日问题（`questions`）

问题采用“今天我是否尽力……”的形式，按 1 至 10 分评分，源自 Marshall Goldsmith 的《Triggers》。评估的是努力程度，而不是结果。系统自带的六个问题是 Goldsmith 的通用问题组。

你可以修改问题文字、重命名键、添加或删除条目。重命名时请保留 `dq_` 前缀，并使用小写字母且不含空格。新建每日笔记会自动采用这里的列表；日终提示会按此处顺序提问；仪表盘会自动发现所有 `dq_*` 属性。

如果更喜欢视频中 Mike Schmitz 使用的问题组，可以用以下内容替换上方列表：

```yaml
questions:
  - {key: dq_spiritual, text: 今天我是否尽力促进心灵成长？}
  - {key: dq_spouse, text: 今天我是否尽力关爱伴侣？}
  - {key: dq_kids, text: 今天我是否尽力关爱孩子？}
  - {key: dq_friend, text: 今天我是否尽力做一个好朋友？}
  - {key: dq_learn, text: 今天我是否尽力学习新知识？}
  - {key: dq_create, text: 今天我是否尽力进行创作？}
  - {key: dq_exercise, text: 今天我是否尽力锻炼身体？}
```

## 习惯（`habits`）

这里列出的项目会作为复选框属性添加到每篇新建的每日笔记中。建议每个阶段保留 3 至 5 项，并使用 `habit_` 前缀。

## 生命之轮（`wheel_areas`）

这里列出的数字属性会添加到每篇新建的个人静修复盘笔记中，评分范围为 1 至 10。你可以自由重命名，但需保留 `wheel_` 前缀；雷达图会根据属性键自动生成标签。

## 文件夹和前缀

| 属性 | 使用位置 |
| --- | --- |
| `daily_folder`、`weekly_folder`、`quarterly_folder`、`retreat_folder`、`projects_folder` | 仪表盘组件和快捷链接；必须与 Periodic Notes 的设置一致 |
| `dq_prefix`、`habit_prefix`、`wheel_prefix` | 用于自动发现属性 |
| `board_done_lanes` | 在“看板”仪表盘中计为已完成的看板分栏 |

如果不使用英文，可以重命名键（例如 `dq_aprender`）并翻译 `text` 的值；图表会根据属性键自动生成标签。系统内部路径、前缀和代码键应保持不变。

## 自动化（Omarchy）

`automation` 只给 `integrations/omarchy` 的 `compass` 命令使用。仪表盘不读它。

| 属性 | 说明 |
| --- | --- |
| `enabled` | 为 false 时，定时任务和提醒都不跑。状态栏仍会更新。 |
| `vault_path` | 留空表示使用这份配置所在的库。安装到另一份库时再填绝对路径。 |
| `quiet_hours` | 这段时间不发提醒，格式 `HH:MM-HH:MM`，可以跨过午夜。简报和复盘不看这个字段。 |
| `max_nudges_per_day` | 每天最多几条规则提醒。 |
| `task_exclude` | 统计到期和逾期时跳过的路径前缀。阅读计划默认排除。 |
| `jobs` | 每个任务的时间。改时间后，下一次 `compass tick` 会按新时间跑。计时器本身每 15 分钟醒来一次。 |
| `activity.categories` | 前台应用类名里包含这些词时，归入该类别。原始记录不进库，也不含窗口标题。 |
| `activity.exclude` | 这些类名不计数，例如锁屏。 |
