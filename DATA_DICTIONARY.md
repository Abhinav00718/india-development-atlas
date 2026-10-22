# Data Dictionary: India Development Atlas

This document describes the indicators displayed by the application. The `INDICATORS` dictionary and data-loading functions in `app-3.py` are the implementation reference. Verify the underlying source table before publishing a value as independently validated.

## Common fields

| Field | Meaning |
|---|---|
| `Region` | Canonical region name used to join indicator records to map boundaries. |
| `Region_Type` | State or Union Territory classification used by the application. |
| `Year` | Numeric reference year used in the source CSV. For fiscal-year series, the app may use the fiscal year's ending year. |
| Indicator-specific numeric column | The observation for that indicator. Blank or non-numeric values are treated as unavailable. |
| `Source` | Source label carried in the dataset where available. |
| `Notes` | Additional context or limitations where available. |

## Indicators

| Display name | CSV file | Numeric column | Unit | Source / definition notes |
|---|---|---|---|---|
| Poverty rate (%) | `india_poverty_rate_2011_12.csv` | `Poverty_Rate_Percent` | Percent | Combined rural and urban poverty ratio, Tendulkar methodology, 2011–12. Historical; current state boundaries may not align with the source's state structure. |
| Multidimensional poverty (%) | `india_mpi_niti_aayog_2023.csv` | `Multidimensional_Poverty_Percent` | Percent | NITI Aayog National Multidimensional Poverty Index, 2023, as described by the project. |
| Literacy rate (%) | `india_literacy_2025.csv` | `Literacy_Rate_Percent` | Percent | The exact population, survey definition, and reference period should be checked against the cited source before interpretation. |
| Per-capita GSDP (₹) | `india_gdp_per_capita_gsdp_2019_2024.csv` | `GDP_Per_Capita_INR` | Indian rupees per person | GSDP per person at current prices. The accompanying repository notes identify a Rajya Sabha answer dated 10 December 2024 as the source. Fiscal year is labelled by ending year. |
| Unemployment rate (%) | `india_unemployment_plfs_2025.csv` | `Unemployment_Rate_Percent` | Percent | Project description specifies usual-status (ps+ss), all ages, rural and urban persons, PLFS 2025. Confirm the exact source table and column before external publication. |
| School enrolment (%) | `india_school_enrolment_secondary_2024_25.csv` | `School_Enrolment_Percent` | Percent | Secondary gross enrolment ratio, Classes IX–X, 2024–25. Gross enrolment ratio can exceed 100%. |
| Health expenditure per capita (₹) | `india_health_expenditure_per_capita_2017_2022.csv` | `Health_Expenditure_Per_Capita_INR` | Indian rupees per person | Per-capita total government health expenditure, FY 2017–18 to FY 2021–22. It is not total public-plus-private health expenditure. |
| Per-capita power availability (kWh) | `india_per_capita_power_availability_2024_25.csv` | `Per_Capita_Power_Availability_kWh` | kWh per person | Per-capita power availability for FY 2024–25. Availability is not the same measure as household electricity consumption. Repository notes identify RBI Handbook of Statistics / Dataful as references. |

## Geographic file

`india_states_ut_simplified.geojson` supplies the shapes used for the choropleth map. The application maps GeoJSON features to the canonical `Region` names. Do not regenerate or replace this file casually: region names and geometries must continue to match the app's region list.

## Missing observations

A missing value means that the app does not have a usable observation for that region-indicator combination in the loaded data. It does **not** mean zero, and it does not necessarily mean the underlying statistic was never collected. Reasons can include source coverage, historical boundary mismatch, extraction gaps, or unavailable published values.
