# India Development Atlas

An interactive Streamlit application for exploring socioeconomic differences across Indian states and Union Territories.

**Live repository:** https://github.com/Abhinav00718/india-development-atlas

## Project goals

The Atlas brings together selected state- and Union-Territory-level indicators in one place. It is intended to support exploration, comparison, and discussion of regional development patterns. It is a descriptive data tool, not a causal model or an official government statistical publication.

## Features

- **Development Map:** explore an indicator on an interactive map. Regions without a usable observation are shown in a neutral colour rather than being assigned zero.
- **State Rankings:** rank regions for a selected indicator and inspect unavailable observations.
- **Explore a Region:** inspect the available indicators and context for an individual region.
- **Compare Regions:** compare selected regions across indicators.
- **Economic Relationships Lab:** explore associations between two indicators using a scatter plot, correlation statistic, and fitted linear trend line.
- **Data Quality & Coverage:** inspect the coverage of indicators, reference years, and missing region-level observations; export coverage information as CSV.
- **About & Sources:** review project context and the listed sources.

The exact pages and indicator set are defined in `app-3.py`; update this README if the application changes.

## Indicators currently included

| Indicator | Unit | Important interpretation note |
|---|---|---|
| Poverty rate | Percent | Historical state poverty estimates are for 2011–12 and should not be presented as current. |
| Multidimensional poverty | Percent | Based on the NITI Aayog National MPI source listed in the application. |
| Literacy rate | Percent | Check the source definition and reference year before comparing it with other literacy series. |
| Per-capita GSDP | Indian rupees | Current-price measure; fiscal-year labels and coverage vary. |
| Unemployment rate | Percent | Interpret alongside the precise PLFS measure, population, and reference period. |
| School enrolment | Percent | Secondary gross enrolment ratio; GER can exceed 100%. |
| Health expenditure per capita | Indian rupees | Government health expenditure per person, not total public-plus-private health spending. |
| Per-capita power availability | kWh per person | Electricity availability is not the same as household electricity consumption. |

Not every indicator has a value for every region or year. See `DATA_DICTIONARY.md` and `METHODOLOGY.md`.

## Technology

- Python
- Streamlit
- pandas
- Plotly
- Requests
- CSV data files and a GeoJSON boundary file hosted in this repository

## Run locally

1. Install Python 3.10 or newer.
2. Clone or download this repository.
3. Install the packages used by the app:

   ```bash
   pip install streamlit pandas plotly requests
   ```

4. Run the application:

   ```bash
   streamlit run app-3.py
   ```

The app loads data and boundaries from the repository's raw GitHub URLs. An internet connection is required.

## Data and limitations

- Missing values are not zeros and should not be interpreted as evidence of no poverty, no unemployment, or no service provision.
- Indicators can have different reference years, definitions, source institutions, and geographic coverage.
- State reorganisations and changes in statistical definitions can limit comparisons over time.
- Some data files contain values that still require row-by-row source verification. The presence of a source label does not itself establish that every value has been independently audited.
- Correlations in the Economic Relationships Lab are descriptive. They do not establish causation and may combine observations from different years.

## Reproducibility and change management

Keep the existing working app as a stable baseline. Make future changes in small increments, preserve the current GeoJSON unless a boundary change is specifically required, and check the items in `QA_CHECKLIST.md` after each code change.

## Suggested citation

Abhinav BJ. *India Development Atlas* [interactive data application]. GitHub repository: https://github.com/Abhinav00718/india-development-atlas. Accessed [insert date].

## Repository contents

- `app-3.py` — Streamlit application.
- `india_states_ut_simplified.geojson` — geographic boundaries used by the maps.
- Indicator-specific CSV files — regional observations and source notes.
- `README.txt` — notes accompanying the indicator CSV pack.
- `DATA_DICTIONARY.md` — indicator definitions and interpretation cautions.
- `METHODOLOGY.md` — data handling and analytical methodology.
- `CHANGELOG.md` — record of project changes.
- `QA_CHECKLIST.md` — manual regression checks before publishing updates.
