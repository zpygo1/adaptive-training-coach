#!/usr/bin/env python3
"""Render a single plan JSON into matching Markdown, offline HTML and optional PNG cards."""
import argparse
import hashlib
import html
import json
import re
import sys
from datetime import date
from pathlib import Path

TOP = ('training_id', 'date', 'version', 'title', 'goal', 'duration', 'rationale')
EXERCISE = ('name', 'purpose', 'load', 'dose', 'rest', 'setup', 'cues', 'adjust', 'progress', 'alternative')
LISTS = ('warmup', 'adjustments', 'stop_rules', 'feedback')
CSS = '''
*{box-sizing:border-box}html,body{margin:0;padding:0;background:#e8ede9;color:#172b25}
body{font-family:"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif;font-size:17px;line-height:1.65}
.card{width:440px;padding:26px 24px 22px;background:#f8faf6;border-top:8px solid #24765c;overflow-wrap:anywhere}
.kicker{font-size:12px;letter-spacing:1.2px;color:#34735c;font-weight:700}.meta{font-size:13px;color:#5b6d64}
h1{font-size:29px;line-height:1.3;margin:12px 0}h2{font-size:21px;margin:22px 0 8px}h3{font-size:20px;line-height:1.4;margin:0 0 10px}
p{margin:7px 0}ul{padding-left:22px;margin:7px 0}li{margin:5px 0}.box{background:#eaf2e9;border-radius:14px;padding:15px;margin:16px 0}
.exercise{border-top:1px solid #ced9ce;padding-top:19px;margin-top:20px}.dose{font-size:18px;font-weight:700;color:#176044}
.label{font-weight:700}.small{font-size:14px;color:#52665b}.footer{border-top:1px solid #ced9ce;margin-top:24px;padding-top:12px;font-size:12px;color:#52665b}
'''


def nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be a nonempty string')


def string_list(value, label):
    if not isinstance(value, list) or not value:
        raise ValueError(f'{label} must be a nonempty list')
    for item in value:
        nonempty(item, label)


def validate(plan):
    if not isinstance(plan, dict):
        raise ValueError('plan must be an object')
    for key in TOP:
        nonempty(plan.get(key), key)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', plan['training_id']):
        raise ValueError('training_id must be a portable ID (letters, numbers, _ or -)')
    if not re.fullmatch(r'v[1-9][0-9]*', plan['version']):
        raise ValueError('version must be v1, v2, ...')
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', plan['date']):
        raise ValueError('date must be YYYY-MM-DD')
    date.fromisoformat(plan['date'])
    for key in LISTS:
        string_list(plan.get(key), key)
    exercises = plan.get('exercises')
    if not isinstance(exercises, list) or not exercises:
        raise ValueError('exercises must be a nonempty list')
    for i, exercise in enumerate(exercises):
        if not isinstance(exercise, dict):
            raise ValueError(f'exercises[{i}] must be an object')
        for key in EXERCISE:
            if key == 'cues':
                string_list(exercise.get(key), f'exercises[{i}].{key}')
            else:
                nonempty(exercise.get(key), f'exercises[{i}].{key}')
    return plan


def canonical(plan):
    return json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def escape(value):
    return html.escape(str(value), quote=True)


def ul(values):
    return '<ul>' + ''.join(f'<li>{escape(value)}</li>' for value in values) + '</ul>'


def field(label, value):
    return f'<p><span class="label">{label}：</span>{escape(value)}</p>'


def exercise_html(index, ex):
    return ('<section class="exercise">'
            f'<h3>{index:02d} · {escape(ex["name"])}</h3>'
            f'<p class="dose">{escape(ex["dose"])}</p>'
            + field('负荷', ex['load']) + field('休息', ex['rest'])
            + field('目的', ex['purpose']) + field('准备', ex['setup'])
            + ul(ex['cues']) + field('当次加减', ex['adjust'])
            + field('下次进阶', ex['progress']) + field('替代', ex['alternative'])
            + '</section>')


def documents(plan, digest):
    intro = ('<div class="box">' + field('本次重点', plan['goal'])
             + f'<p>{escape(plan["rationale"])}</p></div>'
             + '<h2>热身与准备</h2>' + ul(plan['warmup']))
    # One exercise per card: long cues stay readable without shrinking text.
    chunks = [intro] + [exercise_html(i, ex) for i, ex in enumerate(plan['exercises'], 1)]
    chunks += ['<h2>临场调整</h2>' + ul(plan['adjustments'])
               + '<h2>停止条件</h2>' + ul(plan['stop_rules'])
               + '<h2>练完反馈</h2>' + ul(plan['feedback'])]
    pages = []
    for i, body in enumerate(chunks, 1):
        pages.append('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
                     '<meta name="viewport" content="width=device-width, initial-scale=1">'
                     '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
                     f'<title>{escape(plan["title"])}</title><style>{CSS}</style></head><body>'
                     '<main class="card"><div class="kicker">TRAINING / 当日训练</div>'
                     f'<h1>{escape(plan["title"])}</h1>'
                     f'<div class="meta">{escape(plan["date"])} · {escape(plan["version"])} · {escape(plan["duration"])}</div>'
                     + body + f'<footer class="footer">{escape(plan["training_id"])} · {i}/{len(chunks)} · '
                     f'数据校验 {digest[:10]}<br>依次查看全部卡片；修订后使用新版本。</footer></main></body></html>')
    return pages


def markdown(plan):
    lines = [f'# {plan["title"]}', '', f'{plan["date"]} · {plan["version"]} · {plan["duration"]}', '',
             f'训练 ID：{plan["training_id"]}', '', '## 今日结论与安排依据', '',
             f'本次重点：{plan["goal"]}', '', plan['rationale'], '', '## 热身与准备', '']
    lines.extend('- ' + value for value in plan['warmup'])
    for i, ex in enumerate(plan['exercises'], 1):
        lines.extend(['', f'## {i}. {ex["name"]}', '', f'**{ex["dose"]}**', ''])
        for key, label in [('purpose', '目的'), ('load', '负荷'), ('rest', '休息'), ('setup', '准备')]:
            lines.extend([f'{label}：{ex[key]}', ''])
        lines.extend('- ' + value for value in ex['cues'])
        for key, label in [('adjust', '当次加减'), ('progress', '下次进阶'), ('alternative', '替代')]:
            lines.extend(['', f'{label}：{ex[key]}'])
    for key, label in [('adjustments', '临场调整'), ('stop_rules', '停止条件'), ('feedback', '练完反馈')]:
        lines.extend(['', f'## {label}', ''])
        lines.extend('- ' + value for value in plan[key])
    return '\n'.join(lines) + '\n'


def screenshot(directory, files, channel=None):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError('PNG requires Playwright: python -m pip install playwright; python -m playwright install chromium. HTML/Markdown are saved.') from exc
    with sync_playwright() as playwright:
        kwargs = {'headless': True}
        if channel:
            kwargs['channel'] = channel
        with playwright.chromium.launch(**kwargs) as browser:
            page = browser.new_page(viewport={'width': 440, 'height': 900}, device_scale_factor=2)
            # Only local documents; never load remote images, fonts or telemetry.
            page.route('**/*', lambda route: route.continue_() if route.request.url.startswith('file:') else route.abort())
            for name in files:
                page.goto((directory / name).as_uri(), wait_until='load')
                page.evaluate('document.fonts.ready')
                if page.evaluate('document.documentElement.scrollWidth > 440'):
                    raise RuntimeError(f'Horizontal overflow: {name}')
                page.locator('.card').screenshot(path=str((directory / name).with_suffix('.png')))


def render(plan, output_dir, png=False, channel=None):
    validate(plan)
    directory = Path(output_dir).expanduser().resolve()
    if directory.exists() and any(directory.iterdir()):
        raise ValueError('Output directory is not empty; use a new revision directory to preserve previous cards')
    directory.mkdir(parents=True, exist_ok=True)
    data = canonical(plan)
    digest = hashlib.sha256(data.encode('utf-8')).hexdigest()
    (directory / 'plan.json').write_text(data, encoding='utf-8')
    (directory / 'plan.md').write_text(markdown(plan), encoding='utf-8')
    names = []
    for i, document in enumerate(documents(plan, digest), 1):
        name = f'card-{i:02d}.html'
        (directory / name).write_text(document, encoding='utf-8')
        names.append(name)
    manifest = {'training_id': plan['training_id'], 'version': plan['version'], 'sha256': digest,
                'html': names, 'png': [], 'png_status': 'not_requested'}
    manifest_path = directory / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if png:
        try:
            screenshot(directory, names, channel)
            manifest['png'] = [name.replace('.html', '.png') for name in names]
            manifest['png_status'] = 'complete'
        except Exception as exc:
            manifest['png_status'] = 'failed'
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            raise RuntimeError(f'PNG export failed. HTML/Markdown preserved; use a fresh output directory to retry. {exc}') from exc
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return directory, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--png', action='store_true')
    parser.add_argument('--browser-channel', choices=['chrome', 'msedge'], help='Use an installed browser instead of bundled Chromium')
    args = parser.parse_args()
    try:
        plan = json.loads(args.input.read_text(encoding='utf-8'))
        directory, manifest = render(plan, args.output_dir, args.png, args.browser_channel)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    print(f'Saved: {directory}\nCards: {len(manifest["html"])}; PNG: {manifest["png_status"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
