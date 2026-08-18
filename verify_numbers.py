import json

with open('/Users/richa.ranjan/CascadeProjects/search-cases-dashboard/data.json') as f:
    data = json.load(f)

ws_list = ['AI Search Setup & Misc', 'Search Relevancy', 'External Content Connectors', 'Genius Results', 'Search Analytics']
months = ['2026-03', '2026-04', '2026-05', '2026-06']

month_totals = {}
ws_counts = {ws: {m: 0 for m in months} for ws in ws_list}

for r in data['main']:
    m = r['Month Opened']
    ws = r['Bucket']
    if m in months:
        month_totals[m] = month_totals.get(m, 0) + 1
        if ws in ws_counts:
            ws_counts[ws][m] += 1

for m in months:
    t = month_totals.get(m, 0)
    print(f"{m}: total={t}")
    for ws in ws_list:
        c = ws_counts[ws][m]
        print(f"  {ws}: {c} ({c/t*100:.1f}%)")

print('\n=== EXTERNAL CONTENT CONNECTORS ===')
for r in data['main']:
    if r['Bucket'] == 'External Content Connectors':
        print(f"{r['Cases']} | {r['Month Opened']} | {r['Subject'][:70]}")

print('\n=== GENIUS RESULTS ===')
for r in data['main']:
    if r['Bucket'] == 'Genius Results':
        print(f"{r['Cases']} | {r['Month Opened']} | {r['Subject'][:70]}")
