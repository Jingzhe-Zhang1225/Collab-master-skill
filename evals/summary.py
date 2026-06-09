import json, os

# Find the latest tool output
out_dir = os.path.expandvars(r'%USERPROFILE%\.local\share\opencode\tool-output')
files = sorted([f for f in os.listdir(out_dir) if f.endswith('.json') or f.startswith('tool_')],
               key=lambda x: os.path.getmtime(os.path.join(out_dir, x)), reverse=True)

for f in files[:3]:
    path = os.path.join(out_dir, f)
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        s = data.get('summary', {})
        print(f'{f}: total={s.get("total",0)}, passed={s.get("passed",0)}, failed={s.get("failed",0)}')
    except:
        pass
