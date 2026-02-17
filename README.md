# NYCF_BioKind

Quick exploratory analysis for BioKind's donor/marketing support work with NYCF (New York Cancer Foundation).

## Data Used

- Source workbook: `data/NYCFBiokindData.xlsx`
- Converted CSV: `data/NYCFBiokindData_Sheet1.csv`
- Analysis script: `analysis/analyze_nycf_data.py`

## Quick Findings (Current Snapshot)

- **Total records:** 4,462
- **Columns:** 10
- **Organization field:** all rows are `New York Cancer Foundation`
- **Status split:**
	- `Active`: 4,197
	- `DoNotContact`: 265
- **Donation distribution:**
	- Parsed donation values for all 4,462 rows
	- Total donations: **$10,658,637.30**
	- Mean: **$2,388.76**
	- Median: **$0.00**
	- Max: **$325,000.00**
	- Rows with `$0` donation: **2,494**

### Donor Value Segments

- `0`: 2,494
- `1-25`: 234
- `26-100`: 509
- `101-500`: 450
- `501-2.5k`: 420
- `2.5k-10k`: 186
- `10k+`: 169

## Data Quality Notes

- Missing values are high in location fields:
	- `city`: 56.4% missing
	- `state`: 56.7% missing
	- `zip code`: 56.6% missing
- `extension` is 100% missing
- `phone type` is almost entirely `Unknown`

## What We Can Do Next for NYCF

1. **Donor segmentation:** build target groups (non-donor, small, mid, major).
2. **Major donor strategy:** prioritize the `10k+` cohort and identify upgrade candidates in `501-2.5k`.
3. **Reactivation campaign:** target `$0` segment with tailored outreach.
4. **Data cleanup/enrichment:** improve city/state/zip and contact fields before deeper campaign attribution analysis.