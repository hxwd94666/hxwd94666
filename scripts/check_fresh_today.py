"""Exit 0 only when every required module is fresh for today (Asia/Shanghai)."""
import argparse
import json
from pathlib import Path
from refresh_state import due_modules, today_local


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--force',action='store_true')
    args=parser.parse_args()
    try:
        data=json.loads((args.root/'data/stats.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):
        data={}
    today=today_local()
    due=due_modules(data,today,args.force)
    print(f'today={today} due={",".join(due) or "none"} fresh={not due} force={args.force}')
    return 1 if due else 0


if __name__=='__main__':
    raise SystemExit(main())
