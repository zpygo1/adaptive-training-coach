# 手机训练卡与单一计划数据

## 数据格式

参照 [完整虚构示例](../assets/sample-plan.json)。不得把示例直接当用户处方。所有字段必填，未知负荷用明确试重方法，不能写成空值：

- training_id：仅字母、数字、连字符或下划线；同一次训练修订沿用 ID。
- date：用户当地日期 YYYY-MM-DD；version：v1、v2 等。
- title、goal、duration、rationale：标题、本次目标、时长及融入阶段主线的安排依据。
- warmup：热身、准备组及转换的文字数组。
- exercises：按执行顺序，每项包含 name、purpose、load、dose、rest、setup、cues（数组）、adjust、progress、alternative。
- adjustments、stop_rules、feedback：临场处理、停止条件、反馈请求的文字数组。

默认由同一 JSON 导出 Markdown 和 HTML，文字展示与图片使用这份数据，不能分别手抄改写处方。休息日用明确的休息/复查安排作为一个条目，负荷和进阶等字段说明“不适用及恢复训练检查条件”，不得为了满足格式硬加训练。

## 导出命令

以下路径相对于 Skill 目录；实际执行用已定位的 Skill 目录，不写死作者路径。

```bash
python3 scripts/render_plan.py --input /private/path/plan-v1.json --output-dir /private/path/exports-v1
```

Python 3.10+ 标准库即可生成 plan.json、plan.md、分卡 HTML 和 manifest.json。向用户展示 plan.md 的完整内容；HTML 是本地排版中间件，不需要公开网页。

用户同意出图后，使用具备 Playwright 的 Python 环境重新导出到新目录：

```bash
python3 -m venv /private/path/card-env
/private/path/card-env/bin/python -m pip install playwright
/private/path/card-env/bin/python -m playwright install chromium
/private/path/card-env/bin/python scripts/render_plan.py --input /private/path/plan-v1.json --output-dir /private/path/exports-v1-png --png
```

Windows 的虚拟环境解释器为 `card-env\Scripts\python.exe`。已安装 Chrome/Edge 时可尝试 `--browser-channel chrome` 或 `msedge`，无须另装 Chromium。缺依赖时先说明并沿用 HTML/Markdown，不能宣称 PNG 已完成；不要未经用户要求反复安装工具。

## 一致性与可读性

- 本地 HTML/CSS → Chromium 截图 PNG；不调用图像生成模型，不使用远程字体、图片或统计请求。
- 每张逻辑宽度 440px，以 2 倍输出。按“说明与热身 / 每个动作 / 调整与反馈”拆卡；内容增加自动变高，不缩字或裁切。
- 每张含日期、版本、训练 ID、页码和计划摘要哈希。manifest 的 sha256 是同目录 plan.json 的真实 SHA-256，可核对图文来源。
- 卡片包含完整关键内容；提醒用户依次看完全部卡，不单看某一动作。
- 不覆盖非空导出目录；修订后递增版本，用新目录并更新记录中的当前版本，明确旧图已被替代。
- PNG 失败保留文字与 HTML，manifest 标 failed，不报成功；重试用新目录。
- 打开实际 PNG 检查中文、断行、横向溢出、文字是否过小，之后才交付。平台支持时内嵌或附上图片文件，不只发 HTML 链接。
