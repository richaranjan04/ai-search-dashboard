"""
refresh_data.py
---------------
Run this script each time you have new data to update the dashboard.

Usage:
    python3 refresh_data.py

The script reads the Overall Cases file, filters to Product/Service = 'AI Search',
classifies each case into a workstream, and writes data.json for the dashboard.
"""

import pandas as pd
import json
import re
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent
OUTPUT_FILE = DATA_DIR / 'data.json'
# ─────────────────────────────────────────────────────────────────────────────

# ── BUCKET DEFINITIONS ────────────────────────────────────────────────────────
# Priority order: more specific buckets first, broad Setup last, Needs Review fallback.
# Each bucket: (name, [(field, pattern), ...])
# field: 'subject' = subject only, 'full' = subject + description

BUCKET_RULES = [
    ('Zing Search', [
        ('subject', r'\bzing\b'),
        ('full',    r'\bzing search\b'),
    ]),
    ('Migration & Upgrades', [
        ('full', r'\b(migrat|migration|upgrade|patch\s+\d|post.upgrade|pre.upgrade)\b'),
    ]),
    ('External Content Connectors', [
        ('full', r'\b(connector|external source|external content|sharepoint connector|crawl|'
                 r'web crawl|external kb|external knowledge)\b'),
        ('full', r'sharepoint.*search|search.*sharepoint'),
    ]),
    ('Genius Results', [
        ('full', r'\b(genius result|genius results)\b'),
        ('full', r'\bnow assist\b.{0,80}\bgenius\b'),
        ('full', r'\b(genius)\b.{0,60}\b(result|search|format|display|link|order)\b'),
    ]),
    ('Virtual Agent', [
        ('full', r'\b(virtual agent|nava|va search|va profile|va context|now assist.*va|'
                 r'va.*now assist|now assist chatbot|suggested steps generation|'
                 r'agentic workflow|agentic wf|agent workspace|nlu.*search|search.*nlu)\b'),
        ('full', r'\bnow assist\b.{0,80}\b(virtual agent|va search|agent workspace|chatbot)\b'),
    ]),
    ('Search Analytics', [
        ('full', r'\b(search analytics|analytics dashboard|signal log|search signal|'
                 r'sys_search_event|search event|search tracking|search term|'
                 r'sustained reduction.*search|search.*reduction)\b'),
    ]),
    ('Security & Access', [
        ('full', r'\b(permission|access control|role.*search|search.*role|user criteria|'
                 r'visibility|restricted.*search|search.*restrict|moderator|'
                 r'acl|access right|not authorized|unauthorized|guest account|'
                 r'security.*search|search.*security|access.*search|search.*access|'
                 r'cannot see|cannot view|not able to see|not able to view|'
                 r'restricted knowledge|content.*surfaced|surfaced.*content)\b'),
    ]),
    ('Search Relevancy', [
        ('full', r'\b(relevancy|relevance|ranking|multilingual|personali|context graph|'
                 r'inaccurate result|wrong result|no result|not returning|irrelevant|'
                 r'different result|incorrect result|incorrect answer|machine learning|'
                 r'recommended action|result improvement rule|boost action|boost catalog|boost.*search|'
                 r'fuzzy|web search result|prioriti|language.*search|'
                 r'search.*language|boosting|search.*slow|slow.*search|search.*speed|'
                 r'search.*latency|latency.*search|search.*accuracy|accuracy.*search|'
                 r'not relevant|poor result|result.*quality|hybrid search|semantic|'
                 r'rag retriev|rag result|retrieval|inconsistent result)\b'),
    ]),
    ('AI Search Setup & Misc', [
        ('full', r'\b(provision|activat|not activated|not get activated|not getting activated|'
                 r'not enabled|plugin|publish.*search|search.*publish|search profile|'
                 r'indexed source|index source|index event|index queue|index all table|'
                 r'index.*not process|not.*process.*index|reindex|re.index|'
                 r'indexing|misconfigur|lack of transparency|validat|ais_|'
                 r'datasource|search source|search bar|knowledge base|kb article|'
                 r'setup|enable ai search|admin console|activation|status page|'
                 r'ais status|not available.*search|not ready|not completed|'
                 r'dictionary|spell check|catalog item.*search|search.*catalog|'
                 r'not showing.*search|not found.*search|not display.*search|'
                 r'not appear.*search|self.hosted.*search|airgap|ml trainer|ml predictor|'
                 r'queue.*ais|ais.*queue|high ais|ais index|excessive.*ais|influx.*ais|'
                 r'search.*not working|not working.*search|search.*broken|broken.*search|'
                 r'search.*stopped|stopped.*search|search.*error|error.*search|'
                 r'search.*configure|configure.*search|search.*config|config.*search|'
                 r'search.*setup|setup.*search|search.*admin|admin.*search|'
                 r'search.*portal|portal.*search|search.*instance|instance.*search|'
                 r'search.*stuck|stuck.*search|search.*fail|fail.*search)\b'),
    ]),
]


# Manual overrides — cases that need explicit classification regardless of keywords
MANUAL_OVERRIDES = {
    # AI Search Setup & Misc
    'CS9109395': 'AI Search Setup & Misc',
    'CS9198143': 'AI Search Setup & Misc',
    'CS9079259': 'AI Search Setup & Misc',
    'CS9072349': 'AI Search Setup & Misc',
    'CS9249548': 'AI Search Setup & Misc',
    'CS9256395': 'AI Search Setup & Misc',
    'CS9173363': 'AI Search Setup & Misc',
    'CS9048522': 'AI Search Setup & Misc',
    'CS9097996': 'AI Search Setup & Misc',
    'CS9151502': 'AI Search Setup & Misc',
    'CS9093636': 'AI Search Setup & Misc',
    'CS9190532': 'AI Search Setup & Misc',
    'CS9266528': 'AI Search Setup & Misc',
    'CS9063508': 'AI Search Setup & Misc',
    'CS9265054': 'AI Search Setup & Misc',
    'CS9280892': 'AI Search Setup & Misc',
    'CS9249038': 'AI Search Setup & Misc',
    'CS9125363': 'AI Search Setup & Misc',
    'CS9066199': 'AI Search Setup & Misc',
    'CS9109904': 'AI Search Setup & Misc',
    'CS9194471': 'AI Search Setup & Misc',
    'CS9137340': 'AI Search Setup & Misc',
    'CS9260209': 'AI Search Setup & Misc',
    'CS9082270': 'AI Search Setup & Misc',
    'CS9055954': 'AI Search Setup & Misc',
    'CS9211125': 'AI Search Setup & Misc',
    'CS9272569': 'AI Search Setup & Misc',
    'CS9216749': 'AI Search Setup & Misc',
    'CS9182037': 'AI Search Setup & Misc',
    'CS9216590': 'AI Search Setup & Misc',
    'CS9178979': 'AI Search Setup & Misc',
    'CS9216595': 'AI Search Setup & Misc',
    'CS9216580': 'AI Search Setup & Misc',
    'CS9253220': 'AI Search Setup & Misc',
    'CS9200025': 'AI Search Setup & Misc',
    'CS9043984': 'AI Search Setup & Misc',
    'CS9227055': 'AI Search Setup & Misc',
    'CS9100614': 'AI Search Setup & Misc',
    'CS9039533': 'AI Search Setup & Misc',
    'CS9096785': 'AI Search Setup & Misc',
    'CS9066621': 'AI Search Setup & Misc',
    'CS9229736': 'AI Search Setup & Misc',
    'CS9102864': 'AI Search Setup & Misc',
    'CS9225762': 'AI Search Setup & Misc',
    'CS9134321': 'AI Search Setup & Misc',
    'CS9107271': 'AI Search Setup & Misc',
    'CS9105551': 'AI Search Setup & Misc',
    'CS9033401': 'AI Search Setup & Misc',
    'CS9081116': 'AI Search Setup & Misc',
    'CS9113410': 'AI Search Setup & Misc',
    'CS9031380': 'AI Search Setup & Misc',
    'CS9066440': 'AI Search Setup & Misc',
    'CS9090574': 'AI Search Setup & Misc',
    'CS9107232': 'AI Search Setup & Misc',
    'CS9131713': 'AI Search Setup & Misc',
    'CS9099815': 'AI Search Setup & Misc',
    'CS9183423': 'AI Search Setup & Misc',
    'CS9161626': 'AI Search Setup & Misc',
    'CS9263195': 'AI Search Setup & Misc',
    'CS9123515': 'AI Search Setup & Misc',
    'CS9107154': 'AI Search Setup & Misc',
    'CS9176538': 'AI Search Setup & Misc',
    'CS9205321': 'AI Search Setup & Misc',
    'CS9031002': 'AI Search Setup & Misc',
    'CS9155800': 'AI Search Setup & Misc',
    'CS9203944': 'AI Search Setup & Misc',
    'CS9276741': 'AI Search Setup & Misc',
    'CS9055076': 'AI Search Setup & Misc',
    'CS9154782': 'AI Search Setup & Misc',
    'CS9066515': 'AI Search Setup & Misc',
    'CS9155998': 'AI Search Setup & Misc',
    'CS9043411': 'AI Search Setup & Misc',
    'CS9280927': 'AI Search Setup & Misc',
    'CS9198215': 'AI Search Setup & Misc',
    'CS9276759': 'AI Search Setup & Misc',
    'CS9137709': 'AI Search Setup & Misc',
    'CS9180117': 'AI Search Setup & Misc',
    'CS9233015': 'AI Search Setup & Misc',
    'CS9259479': 'AI Search Setup & Misc',
    'CS9098310': 'AI Search Setup & Misc',
    # Search Relevancy
    'CS9160015': 'Search Relevancy',
    'CS9033952': 'Search Relevancy',
    'CS9228775': 'Search Relevancy',
    'CS9077797': 'Search Relevancy',
    'CS9218446': 'Search Relevancy',
    'CS9249774': 'Search Relevancy',
    'CS9160015': 'Search Relevancy',
    'CS9282447': 'Search Relevancy',
    'CS9048862': 'Search Relevancy',
    'CS9183511': 'Search Relevancy',
    'CS9072085': 'Search Relevancy',
    'CS9105876': 'Search Relevancy',
    'CS9253221': 'Search Relevancy',
    'CS9036048': 'Search Relevancy',
    'CS9039115': 'Search Relevancy',
    'CS9253223': 'Search Relevancy',
    'CS9216580': 'Search Relevancy',
    'CS9035912': 'Search Relevancy',
    'CS9066652': 'Search Relevancy',
    'CS9220931': 'Search Relevancy',
    'CS9072393': 'Search Relevancy',
    'CS9091946': 'Search Relevancy',
    'CS9154669': 'Search Relevancy',
    'CS9062476': 'Search Relevancy',
    'CS9037986': 'Search Relevancy',
    'CS9212361': 'Search Relevancy',
    'CS9059672': 'Search Relevancy',
    'CS9095240': 'Search Relevancy',
    'CS9253656': 'Search Relevancy',
    'CS9094225': 'Search Relevancy',
    'CS9102079': 'Search Relevancy',
    'CS9093855': 'Search Relevancy',
    'CS9167728': 'Search Relevancy',
    # Virtual Agent
    'CS9204319': 'Virtual Agent',
    'CS9090732': 'Virtual Agent',
    'CS9263984': 'Virtual Agent',
    'CS9236667': 'Virtual Agent',
    'CS9036117': 'Virtual Agent',
    'CS9268761': 'Virtual Agent',
    'CS9175693': 'Virtual Agent',
    'CS9085874': 'Virtual Agent',
    'CS9076505': 'Virtual Agent',
    'CS9134432': 'Virtual Agent',
    'CS9241294': 'Virtual Agent',
    # Security & Access
    'CS9112448': 'Security & Access',
    'CS9253223': 'Security & Access',
    'CS9093782': 'Security & Access',
    'CS9152575': 'Security & Access',
    # Search Analytics
    'CS9265121': 'Search Analytics',
    'CS9153055': 'Search Analytics',
    'CS9079638': 'Search Analytics',
    'CS9272261': 'Search Analytics',
    # External Content Connectors
    'CS9163387': 'External Content Connectors',
    'CS9226381': 'External Content Connectors',
    'CS9080986': 'External Content Connectors',
    # Misclassified from Analytics
    'CS9041344': 'Search Relevancy',
    'CS9273284': 'Search Relevancy',
    'CS9228918': 'Search Relevancy',
    'CS9161270': 'Security & Access',
    # Final 9
    'CS9258770': 'Search Relevancy',
    'CS9285942': 'AI Search Setup & Misc',
    'CS9123082': 'AI Search Setup & Misc',
    'CS9191275': 'AI Search Setup & Misc',
    'CS9044043': 'AI Search Setup & Misc',
    'CS9241882': 'Search Analytics',
    'CS9182885': 'Search Relevancy',
    'CS9039831': 'AI Search Setup & Misc',
    'CS9229377': 'AI Search Setup & Misc',
    'CS9113432': 'Others',
    'CS9227608': 'Virtual Agent',
    # Others
    'CS9081282': 'Others',
    'CS9030255': 'Others',
    'CS9277153': 'Others',
    'CS9156776': 'Others',
    'CS9163840': 'Others',
    'CS9029485': 'Others',
    'CS9167547': 'Others',
    'CS9037794': 'Others',
    'CS9225948': 'Others',
    'CS9257641': 'Others',
    # Reclassified from split Search & Virtual Agent
    'CS9262324': 'Genius Results',
    'CS9340257': 'Genius Results',
    'CS9340371': 'Genius Results',
    'CS9378469': 'Genius Results',
    'CS9282865': 'AI Search Setup & Misc',
    'CS9331906': 'AI Search Setup & Misc',
    'CS9360413': 'Search Relevancy',
    # July 2026 Needs Review
    'CS9175589': 'AI Search Setup & Misc',
    'CS9158748': 'AI Search Setup & Misc',
    'CS9073118': 'Virtual Agent',
    'CS9120491': 'Others',
    'CS9173312': 'Search Relevancy',
    'CS9256570': 'AI Search Setup & Misc',
    'CS9208182': 'Others',
    'CS9134541': 'AI Search Setup & Misc',
    'CS9111942': 'Others',
    'CS9153242': 'AI Search Setup & Misc',
    'CS9106255': 'Search Relevancy',
    'CS9205752': 'AI Search Setup & Misc',
    'CS9131555': 'AI Search Setup & Misc',
    'CS9270256': 'AI Search Setup & Misc',
    'CS9208432': 'Others',
    'CS9173385': 'Search Relevancy',
    'CS9252019': 'AI Search Setup & Misc',
    # May-June 2026 Needs Review
    'CS9382649': 'Others',
    'CS9294232': 'AI Search Setup & Misc',
    'CS9338797': 'AI Search Setup & Misc',
    'CS9333565': 'Others',
    'CS9296926': 'Others',
    'CS9301400': 'Others',
    'CS9382385': 'Search Relevancy',
    'CS9398936': 'Search Relevancy',
    'CS9375632': 'AI Search Setup & Misc',
    'CS9329252': 'AI Search Setup & Misc',
    'CS9327928': 'AI Search Setup & Misc',
    'CS9330970': 'AI Search Setup & Misc',
    'CS9369051': 'AI Search Setup & Misc',
    'CS9317857': 'Virtual Agent',
    'CS9307973': 'Others',
    'CS9373256': 'Virtual Agent',
    'CS9302497': 'AI Search Setup & Misc',
    'CS9327001': 'Search Relevancy',
    'CS9378679': 'AI Search Setup & Misc',
    'CS9325459': 'Search Analytics',
    'CS9350374': 'Search Relevancy',
    'CS9361293': 'AI Search Setup & Misc',
    'CS9301058': 'AI Search Setup & Misc',
    'CS9302455': 'AI Search Setup & Misc',
    'CS9363797': 'AI Search Setup & Misc',
    'CS9327052': 'AI Search Setup & Misc',
    'CS9336859': 'Virtual Agent',
    'CS9333531': 'Search Relevancy',
    'CS9330271': 'Search Relevancy',
    'CS9398056': 'Search Relevancy',
    'CS9310370': 'AI Search Setup & Misc',
    'CS9303006': 'Virtual Agent',
    'CS9379888': 'AI Search Setup & Misc',
    'CS9356199': 'Search Analytics',
    'CS9376714': 'Virtual Agent',
    'CS9386833': 'Others',
    'CS9379853': 'AI Search Setup & Misc',
    'CS9353734': 'AI Search Setup & Misc',
    'CS9295651': 'Search Analytics',
    'CS9335730': 'Others',
    'CS9346411': 'Search Relevancy',
}


def classify(case_id, subject, description):
    if case_id and case_id in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[case_id]

    subj = str(subject).lower()
    desc = str(description).lower()
    full = subj + ' ' + desc

    for bucket, rules in BUCKET_RULES:
        for field, pattern in rules:
            text = subj if field == 'subject' else full
            if re.search(pattern, text):
                return bucket

    return 'Needs Review'


def to_record(row):
    return {
        'Cases':           str(row.get('Cases', '')),
        'Subject':         str(row.get('Subject', '')),
        'Pri':             str(row.get('Pri', '')),
        'State':           str(row.get('State', '')),
        'Product':         str(row.get('Product', '')),
        'Bucket':          str(row.get('Bucket', '')),
        'Date Opened':     row['Date Opened'].strftime('%Y-%m-%d %H:%M') if pd.notna(row.get('Date Opened')) else '',
        'Date Resolved':   row['Date Resolved'].strftime('%Y-%m-%d %H:%M') if pd.notna(row.get('Date Resolved')) else '',
        'Date Closed':     row['Date Closed'].strftime('%Y-%m-%d %H:%M') if pd.notna(row.get('Date Closed')) else '',
        'Days to Resolve': str(int(row['Days to Resolve'])) if pd.notna(row.get('Days to Resolve')) else '',
        'Month Opened':    str(row.get('Month Opened', '')),
        'Month Closed':    str(row.get('Month Closed', '')),
    }


def main():
    print('Loading data...')

    # Find all Overall Cases files and combine them
    files = sorted(DATA_DIR.glob('Overall Cases*.xlsx'))
    if not files:
        raise FileNotFoundError(f'No Overall Cases*.xlsx files found in {DATA_DIR}')

    print(f'Found {len(files)} file(s): {[f.name for f in files]}')
    parts = []
    for f in files:
        df = pd.read_excel(f, sheet_name='Page 1')
        print(f'  {f.name}: {len(df)} rows')
        parts.append(df)

    overall = pd.concat(parts, ignore_index=True)

    # Deduplicate by case number, keeping the most recent record
    overall = overall.sort_values('Created').drop_duplicates(subset='Number', keep='last')

    # Filter to AI Search cases
    ai_search = overall[overall['Product/service calculated'] == 'AI Search'].copy()
    print(f'Combined overall rows: {len(overall)} | AI Search cases: {len(ai_search)}')

    # Normalize columns
    df = ai_search.rename(columns={
        'Number': 'Cases',
        'Created': 'Date Opened',
        'Resolved': 'Date Resolved',
        'Closed at': 'Date Closed',
        'Priority': 'Pri',
        'Subject': 'Subject',
        'Description': 'Description',
        'Resolution notes': 'Resolution notes',
        'Product/service calculated': 'Product',
    }).copy()

    # Use the plain 'State' column for case state
    if 'State' in df.columns:
        df['State'] = df['State'].astype(str)
    elif 'State(state)' in df.columns:
        df['State'] = df['State(state)'].astype(str)

    for col in ['Date Opened', 'Date Resolved', 'Date Closed']:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    df['Days to Resolve'] = (df['Date Resolved'] - df['Date Opened']).dt.days
    df['Month Opened'] = df['Date Opened'].dt.to_period('M').astype(str)
    df['Month Closed'] = df['Date Closed'].dt.to_period('M').astype(str)

    # Classify
    df['Bucket'] = df.apply(
        lambda r: classify(r.get('Cases', ''), r.get('Subject', ''), r.get('Description', '')), axis=1
    )

    print('\nBucket distribution:')
    print(df['Bucket'].value_counts().to_string())

    needs_review = df[df['Bucket'] == 'Needs Review']
    print(f'\nNeeds Review: {len(needs_review)} cases')

    # Build output
    data = {
        'generated': pd.Timestamp.now().strftime('%Y-%m-%d'),
        'main': [to_record(r) for _, r in df.iterrows()],
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f'\nSaved to: {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
