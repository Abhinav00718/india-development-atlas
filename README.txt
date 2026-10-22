India Development Atlas - complete indicator CSV pack
=======================================================

Included CSV files
------------------
1. india_gdp_per_capita_gsdp_2019_2024.csv
   Official source: Rajya Sabha Unstarred Question 1677, answered 10 Dec 2024.
   PDF: https://sansad.in/getFile/annex/266/AU1677_35H76u.pdf?source=pqars
   Measure: per-capita GSDP at current prices (₹), fiscal years 2019-20 to 2023-24.
   All 28 states are represented. The source marks some state/year values as NA;
   those remain blank. The latest common year with reported values for all states
   in this table is 2021-22, so use 2021-22 for a map requiring complete state coverage.
   In the CSV, Year=2022 means FY 2021-22.

2. india_health_expenditure_per_capita_2017_2022.csv
   Official source: Rajya Sabha Unstarred Question 276, answered 4 Feb 2025.
   PDF: https://sansad.in/getFile/annex/267/AU276_1fzsrW.pdf?source=pqars
   Measure: per-capita total government health expenditure (₹), FY 2017-18 to 2021-22.
   All 28 states are represented. Any values not available in the extracted official
   table are blank, not estimated. This is government health expenditure, not total
   public + private health expenditure. In the CSV, Year=2022 means FY 2021-22.

3. india_poverty_rate_2011_12.csv
   Combined rural + urban poverty ratio, Tendulkar methodology, 2011-12.
   Historical estimates; state reorganization makes some values non-comparable to
   current boundaries. Blank values mean no directly comparable figure.

4. india_unemployment_plfs_2025.csv
   PLFS 2025 unemployment estimates. The measure should be checked against the
   exact official table and column before publication.

5. india_school_enrolment_secondary_2024_25.csv
   Secondary gross enrolment ratio (Classes IX-X), 2024-25. GER can exceed 100.
   Some entries are blank where values were not extracted/verified.

All CSVs retain the Atlas's common schema:
Region, Region_Type, Year, Poverty_Rate_Percent, Multidimensional_Poverty_Percent,
Literacy_Rate_Percent, GDP_Per_Capita_INR, Unemployment_Rate_Percent,
School_Enrolment_Percent, Health_Expenditure_Per_Capita_INR, Source, Notes.

Important data quality note
---------------------------
The GSDP and government health expenditure figures are extracted from official
parliamentary-answer tables. The other three CSVs are carried forward from the
previous pack and should not be described as fully verified until every value has
been cross-checked against its source table.
