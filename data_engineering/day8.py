import numpy as np
import pandas as pd
import os

# 1. Generate sample data
rng = np.random.default_rng(42)
rows = 100_000

df = pd.DataFrame({
    "id": np.arange(1, rows + 1),
    "value": rng.uniform(0, 1000, rows),
    "date": pd.to_datetime("2025-01-01") +
            pd.to_timedelta(rng.integers(0, 365, rows), unit="D"),
    "category": rng.choice(
        ["A", "B", "C", "D", "E"],
        size=rows
    )
})

print("Original DataFrame:")
print(df.head())
print(f"\nRows: {len(df):,}")
print("\nOriginal dtypes:")
print(df.dtypes)


# 2. Save in different formats
df.to_csv("data.csv", index=False)

df.to_json(
    "data.json",
    orient="records",
    lines=True,
    date_format="iso"
)

df.to_parquet("data.parquet", index=False)


# 3. Read files back
datasets = {
    "CSV": pd.read_csv("data.csv", parse_dates=["date"]),
    "JSON": pd.read_json(
        "data.json",
        orient="records",
        lines=True,
        convert_dates=["date"]
    ),
    "Parquet": pd.read_parquet("data.parquet")
}


# 4. Compare file sizes and dtypes
print("\nFile comparison:")

for name, data in datasets.items():
    filename = f"data.{name.lower()}"
    size = os.path.getsize(filename)

    print(f"\n{'=' * 40}")
    print(f"Format: {name}")
    print(f"File size: {size:,} bytes ({size / 1024:.2f} KB)")
    print("\nDtypes:")
    print(data.dtypes)