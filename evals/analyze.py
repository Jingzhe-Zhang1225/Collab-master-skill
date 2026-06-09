import json
from collections import Counter

with open(r'C:\Users\zhangjingzhe\.local\share\opencode\tool-output\tool_eabc04719001dIMoWKYfLRp87a', 'r', encoding='utf-8') as f:
    data = json.load(f)

summary = data['summary']
print(f"Total: {summary['total']}, Passed: {summary['passed']}, Failed: {summary['failed']}")

err_types = Counter()
for r in data['results']:
    if r['status'] == 'fail':
        for e in r.get('errors', []):
            msg = e.get('message', '')[:80]
            if 'Additional properties' in msg:
                err_types['extra_properties'] += 1
            elif 'is not one of' in msg:
                err_types['enum_violation'] += 1
            elif 'required' in msg.lower():
                err_types['missing_required'] += 1
            else:
                err_types[f'other'] += 1

print()
print('Failure classes:')
for k, v in err_types.most_common():
    print(f'  {k}: {v}')
