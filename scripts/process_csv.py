#!/usr/bin/env python3
"""
LRC Dashboard - GitHub Actions processor
Finds the latest CSV in data/, processes it, updates index.html
"""
import os, json, re, csv, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / 'data'
HTML_FILE = ROOT / 'index.html'

DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
MONTHS = ['January','February','March','April','May','June','July',
          'August','September','October','November','December']
STATUS_MAP = {'CANCELED':'Canceled','Student Cancelled':'Canceled','Cancelled':'Canceled'}
KEEP_STATUSES = {'Attended','Missed','Canceled','Needs Review','Forgiven Absence','Tutor Unavailable'}

def parse_hour(s):
    m = re.match(r'(\d+):(\d+)\s*(AM|PM)', str(s or ''), re.IGNORECASE)
    if not m: return 0
    h = int(m.group(1))
    if m.group(3).upper() == 'PM' and h != 12: h += 12
    if m.group(3).upper() == 'AM' and h == 12: h = 0
    return h

def parse_date(s):
    for fmt in ('%m/%d/%Y','%Y-%m-%d','%m/%d/%y','%Y/%m/%d'):
        try: return datetime.strptime(str(s).strip(), fmt)
        except: pass
    return None

def process_csv(filepath):
    with open(filepath, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    if not rows: return None

    parsed_dates = [parse_date(r.get('Date','')) for r in rows]
    valid = [d for d in parsed_dates if d]
    if not valid: return None

    min_date = min(valid).replace(hour=0,minute=0,second=0,microsecond=0)
    max_date = max(valid)

    records = []
    for i, row in enumerate(rows):
        d = parsed_dates[i]
        if not d: continue

        raw_status = str(row.get('Appt Status','')).strip()
        status = STATUS_MAP.get(raw_status, raw_status)
        if status not in KEEP_STATUSES: status = raw_status

        subj = str(row.get('Appt Subject','')).strip() if row.get('Appt Subject') else ''
        if subj and subj.lower() != 'nan':
            code = subj.split()[0]
            m = re.match(r'^([A-Za-z]+)', code)
            dept = m.group(1).upper() if m else 'OTHER'
        else:
            code, dept = 'nan', 'OTHER'

        d0 = d.replace(hour=0,minute=0,second=0,microsecond=0)
        week_num = ((d0 - min_date).days // 7) + 1

        sid_raw = row.get('Student ID') or row.get('Dummy') or '0'
        try: sid = int(float(str(sid_raw).strip()))
        except: sid = 0

        records.append({
            'Date': d.strftime('%Y-%m-%d'),
            'DayOfWeek': DAYS[d.weekday()],
            'Month': MONTHS[d.month-1],
            'WeekNum': week_num,
            'Hour': parse_hour(row.get('Appt Started','')),
            'Status': status,
            'tutor': str(row.get('Appt Consultant','')).strip(),
            'CourseCode': code,
            'Dept': dept,
            'studentId': sid,
            'location': str(row.get('Appt Location', '') or '').strip(),
        })

    return records, min_date, max_date

def update_html(records, min_date, max_date, semester_name):
    html = HTML_FILE.read_text(encoding='utf-8')

    # Replace RAW_RECORDS using split (faster than regex on large JSON)
    marker_start = 'let RAW_RECORDS = ['
    marker_end = '];'
    start_idx = html.index(marker_start)
    end_idx = html.index(marker_end, start_idx) + len(marker_end)
    new_records = f'let RAW_RECORDS = {json.dumps(records, separators=(",",":"))};'
    html = html[:start_idx] + new_records + html[end_idx:]

    # Format dates
    def fmt(d): return d.strftime('%b %-d, %Y')
    subtitle = f'Learning Resource Center &mdash; {fmt(min_date)} – {fmt(max_date)}'
    title_text = f'{semester_name} LRC Appointment/Visit Analytics'

    # Update title elements
    html = re.sub(r'<title>.*?</title>', f'<title>{title_text}</title>', html)
    html = re.sub(r'(<h1 id="dashboardTitle">).*?(</h1>)', rf'\g<1>{title_text}\g<2>', html)
    html = re.sub(r'(<p id="dashboardSubtitle">).*?(</p>)', rf'\g<1>{subtitle}\g<2>', html)
    html = re.sub(r'(<div class="kpi-sub" id="kpiSemesterLabel">).*?(</div>)', rf'\g<1>{semester_name} Semester\g<2>', html)

    HTML_FILE.write_text(html, encoding='utf-8')

def main():
    csvs = list(DATA_DIR.glob('*.csv'))
    if not csvs:
        print('No CSV files found in data/')
        sys.exit(0)

    # Use the file git just changed if available, otherwise sort by name
    changed_env = os.environ.get('CHANGED_CSV', '').strip()
    if changed_env:
        changed_path = ROOT / changed_env
        if changed_path.exists():
            latest = changed_path
            csvs = [p for p in csvs if p != latest] + [latest]
            print(f'Processing (from git): {latest.name}')
        else:
            latest = sorted(csvs, key=lambda p: p.name)[-1]
            print(f'Processing (fallback): {latest.name}')
    else:
        latest = sorted(csvs, key=lambda p: p.name)[-1]
        print(f'Processing (by name): {latest.name}')

    result = process_csv(latest)
    if not result:
        print('ERROR: Could not parse CSV')
        sys.exit(1)

    records, min_date, max_date = result

    # Strip trailing date portion from filename (e.g. "Spring 2026 - 2026-05-27" → "Spring 2026")
    semester_name = re.sub(r'\s*[-_]\s*\d{4}[-/]\d{2}[-/]\d{2}$', '', latest.stem).strip()
    semester_name = re.sub(r'\s*[-_]\s*\d{2}[-/]\d{2}[-/]\d{4}$', '', semester_name).strip()
    if not semester_name:
        semester_name = latest.stem  # fallback to full filename if stripping leaves nothing

    update_html(records, min_date, max_date, semester_name)

    # ── Save semester JSON archive ────────────────────────────────────────────
    semester_json_path = DATA_DIR / f'{semester_name}.json'
    semester_json_path.write_text(json.dumps(records, separators=(',', ':')), encoding='utf-8')
    print(f'Saved semester archive: {semester_json_path.name}')

    # ── Update manifest.json ──────────────────────────────────────────────────
    manifest_path = DATA_DIR / 'manifest.json'
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        except Exception:
            manifest = []
    else:
        manifest = []

    # Remove existing entry with same semester name
    manifest = [e for e in manifest if e.get('name') != semester_name]

    # Add new entry at front
    manifest.insert(0, {
        'name': semester_name,
        'file': f'{semester_name}.json',
        'records': len(records),
        'minDate': min_date.strftime('%Y-%m-%d'),
        'maxDate': max_date.strftime('%Y-%m-%d'),
    })

    # Sort by minDate descending (newest first)
    manifest.sort(key=lambda e: e.get('minDate', ''), reverse=True)

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Updated manifest.json ({len(manifest)} semester(s))')

    # Delete older CSVs -- keep only the most recent (current file)
    for old_csv in csvs[1:]:
        old_csv.unlink()
        print(f'Removed old file: {old_csv.name}')

    print(f'Done: Updated index.html -- {semester_name} | {len(records):,} records | {min_date.strftime("%b %-d")} - {max_date.strftime("%b %-d, %Y")}')

if __name__ == '__main__':
    main()
