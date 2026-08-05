import pandas as pd
import numpy as np

# Load original CSV
df = pd.read_csv('NATIONAL AYURVEDA MORBIDITY CODES.csv')

# Replace problematic header names
new_columns = []
counter = {}
for col in df.columns:
    # Replace numeric or invalid names like '1' with 'field_1'
    if str(col).replace('.', '').isdigit():
        new_col = f"field_{str(col).replace('.', '_')}"
    else:
        new_col = str(col)
    
    # Ensure uniqueness
    if new_col in new_columns:
        count = counter.get(new_col, 1) + 1
        counter[new_col] = count
        new_col = f"{new_col}_{count}"
    new_columns.append(new_col)

# Apply new columns
df.columns = new_columns

# Handle NaN values for MongoDB
df = df.replace({np.nan: None})

# Save cleaned CSV
df.to_csv('NAMC_FINAL.csv', index=False)
print('CSV headers fixed and saved as NAMC_FINAL.csv')
print(f'Columns renamed: {list(zip(df.columns[:5], new_columns[:5]))}')  # Show first 5 mappings

