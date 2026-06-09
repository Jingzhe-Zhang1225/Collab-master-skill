import yaml, json, os, glob

evals_dir = os.path.dirname(os.path.abspath(__file__))
all_cases = []

for yf in sorted(glob.glob(os.path.join(evals_dir, '*.yaml'))):
    with open(yf, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    module = data.get('module', 'unknown')
    for case in data.get('cases', []):
        mc = {
            'id': f"{module}_{case['id']}",
            'quadrant': case.get('quadrant', 'N'),
            'input': case.get('input', {}),
            'expected': case.get('expected', {})
        }
        if 'note' in case:
            mc['note'] = case['note']
        all_cases.append(mc)

out_path = os.path.join(evals_dir, 'all-mock-cases.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(all_cases, f, ensure_ascii=False, indent=2)

print(f'Converted {len(all_cases)} cases → {out_path}')
