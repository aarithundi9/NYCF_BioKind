from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


def sanitize_sheet_name(sheet_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", sheet_name.strip())
    return cleaned.strip("_") or "sheet"


def profile_dataframe(df: pd.DataFrame, name: str) -> None:
    print(f"\n=== Sheet: {name} ===")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")
    print("\nColumns:")
    for col in df.columns:
        null_pct = (df[col].isna().mean() * 100) if len(df) else 0
        print(f"- {col} | dtype={df[col].dtype} | null%={null_pct:.1f}")

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if numeric_cols:
        print("\nTop numeric summaries (mean, median):")
        for col in numeric_cols[:10]:
            series = df[col].dropna()
            if not series.empty:
                print(
                    f"- {col}: mean={series.mean():.2f}, median={series.median():.2f}, max={series.max():.2f}"
                )

    text_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    if text_cols:
        print("\nTop categorical values (first 5 cols):")
        for col in text_cols[:5]:
            vc = df[col].astype("string").fillna("<NA>").value_counts().head(5)
            print(f"- {col}:")
            for key, value in vc.items():
                print(f"    {key}: {value}")


def main() -> None:
    root = Path(__file__).resolve().parent
    xlsx = root / "NYCFBiokindData.xlsx"

    if not xlsx.exists():
        raise FileNotFoundError(f"Could not find {xlsx}")

    excel = pd.ExcelFile(xlsx)
    print("Found sheets:", excel.sheet_names)

    for sheet in excel.sheet_names:
        df = pd.read_excel(xlsx, sheet_name=sheet)
        out_csv = root / f"{xlsx.stem}_{sanitize_sheet_name(sheet)}.csv"
        df.to_csv(out_csv, index=False)
        print(f"Exported: {out_csv.name}")
        profile_dataframe(df, sheet)


if __name__ == "__main__":
    main()
