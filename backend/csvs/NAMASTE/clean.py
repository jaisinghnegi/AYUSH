import pandas as pd
import numpy as np

# Read the CSV file
df = pd.read_csv('NATIONAL AYURVEDA MORBIDITY CODES.csv')

# Fix the column with period
df.columns = [col.replace('Sr No.', 'Sr_No') for col in df.columns]

# Remove duplicate columns if any exist
df = df.loc[:, ~df.columns.duplicated()]

# Handle NaN values for MongoDB
df = df.replace({np.nan: None})

# Save the cleaned CSV
df.to_csv('NAMC_CLEANED.csv', index=False)

