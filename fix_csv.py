import pandas as pd, csv, re, shutil
from datetime import datetime

# Backup first
shutil.copy('complaints.csv', f'complaints_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
print('Backup created.')

df = pd.read_csv('complaints.csv', quoting=csv.QUOTE_MINIMAL, on_bad_lines='skip')
print('Columns before:', list(df.columns))

# Add Media URLs column if missing
if 'Media URLs' not in df.columns:
    df.insert(df.columns.get_loc('Solve Hash') + 1, 'Media URLs', '')
    print('Added Media URLs column after Solve Hash.')

# Pattern to detect media URLs mistakenly in Solve Hash
media_pat = re.compile(r'cloudinary\.com|/static/uploads/complaints/', re.I)

# Fix rows where Solve Hash contains a media URL (not a real tx hash)
fixed = 0
for idx, row in df.iterrows():
    sh = str(row.get('Solve Hash', '') or '')
    if media_pat.search(sh):
        df.at[idx, 'Media URLs'] = sh
        df.at[idx, 'Solve Hash'] = ''
        fixed += 1
        print(f'  Fixed {row["Reference No"]}: moved media URL to Media URLs column')

print(f'\nFixed {fixed} rows.')
print('Columns after:', list(df.columns))

df.to_csv('complaints.csv', index=False, quoting=csv.QUOTE_MINIMAL)
print('Saved complaints.csv successfully.')
