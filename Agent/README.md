# Agent

`integrations/omarchy` 把无人值守运行的记录写在这里。

- `Log/` 是每次运行的追加日志，包含撤销 id。
- `Reports/` 是季度准备和库健康检查的报告。

这些文件可以删掉，但不该放进对外发布的模板。构建脚本会丢掉 `Log/` 和 `Reports/` 里的笔记，只保留空目录。
