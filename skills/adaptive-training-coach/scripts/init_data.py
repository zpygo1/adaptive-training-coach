#!/usr/bin/env python3
"""Create a private training workspace without overwriting any existing files."""
import argparse
from pathlib import Path

TEMPLATES = {
    'profile.md': '# 个人档案\n\n目标及主次：待了解\n训练经历：待了解\n时间与器械：待了解\n已确认运动限制：待了解\n稳定偏好：待了解\n信息日期与来源：待记录\n',
    'program.md': '# 当前阶段（内部）\n\n当前方向：待建档\n阶段重点与观察周期：待制定\n可比锚点与覆盖：待制定\n进阶与调整条件：待制定\n',
    'state.md': '# 当前状态\n\n近期实际训练：尚无确认记录\n带日期的恢复/症状：待了解\n下次优先检查：完成首次建档\n已计数完成 ID：[]\n已复盘覆盖 ID：[]\n待确认问题：[]\n',
    '.gitignore': '# Private training records: do not publish by default.\n*\n',
}


def initialize(directory):
    directory = Path(directory).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    created = []
    for name, content in TEMPLATES.items():
        target = directory / name
        try:
            with target.open('x', encoding='utf-8') as handle:
                handle.write(content)
            created.append(name)
        except FileExistsError:
            pass
    for name in ('sessions', 'reviews'):
        (directory / name).mkdir(exist_ok=True)
    return directory, created


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True)
    args = parser.parse_args()
    directory, created = initialize(args.data_dir)
    print(f'Data directory: {directory}\nCreated: {", ".join(created) or "none (existing records preserved)"}')


if __name__ == '__main__':
    main()
