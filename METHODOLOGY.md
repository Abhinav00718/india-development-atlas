# Methodology and Data Handling

## 1. Purpose

The India Development Atlas is a descriptive application for exploring selected socioeconomic indicators across Indian states and Union Territories. It is designed for transparent exploration, not for estimating causal effects or producing an official composite development index.

## 2. Data inputs

Each indicator is loaded from its own CSV file in the GitHub repository. The geographic layer is a separate GeoJSON file. The application records a display name, numeric column, unit, description, and source label for each indicator.

The source and reference period are not identical across indicators. Some indicators are historical, and some region-level values are unavailable or require further source verification.

## 3. Data validation and region matching

The application normalises region names and validates the expected data columns before displaying results. Numeric indicator fields and years are converted to numeric values; non-numeric entries become missing values. The map relies on canonical region names matching the GeoJSON feature properties.

The map diagnostics panel reports geographic features and region matches. A region that fails geographic matching is different from a region whose boundary is present but whose indicator observation is missing.

## 4. Missing data

Missing values are preserved as missing rather than filled with zero. In the map, regions with unavailable indicator values are intended to remain visible in a neutral colour. Rankings and coverage summaries distinguish available observations from unavailable observations.

Coverage should be read as a property of the current dataset and selected definition. It is not a quality score: a dataset can have complete coverage but still be old, imprecise, or not comparable across regions.

## 5. Rankings

The State Rankings page sorts available observations from highest to lowest or lowest to highest, according to the user's selection. A numerical rank does not automatically mean better or worse development. For example, lower poverty or unemployment is usually interpreted differently from higher income or power availability.

The displayed reference year matters. Rankings across different years should be treated cautiously.

## 6. Economic Relationships Lab

The user selects two indicators and views their region-level relationship as a scatter plot, correlation statistic, and fitted linear trend. The displayed observations can use the latest usable observation available for each region and indicator; therefore, the two axes may not refer to the same year.

Correlation describes the direction and strength of a linear association in the displayed sample. It does not demonstrate causality, control for confounders, or establish that changes in one indicator cause changes in another. Results can be sensitive to outliers, regional differences, missing observations, and mismatched reference years.

## 7. Data Quality & Coverage page

The coverage page summarises whether usable observations are available for region-indicator pairs and exposes missing-data and reference-year information. Coverage results depend on the current files and the app's latest-observation logic. A reported coverage percentage should always be interpreted alongside the indicator definition, source, and reference period.

## 8. Comparability limitations

- **Different periods:** indicators can refer to different years or fiscal years.
- **Different definitions:** measures with similar labels may use different survey populations or methods.
- **Geographic changes:** the creation or reorganisation of states and Union Territories can make older figures difficult to align to present boundaries.
- **Extraction and verification:** some files may include unverified or partially extracted values. These should be cross-checked against official source tables before being used for a formal empirical claim.
- **Descriptive, not causal:** maps, rankings, and correlations are exploratory unless supported by a separate research design.

## 9. Recommended future validation

Before treating the Atlas as a research dataset:
1. Check every CSV's source, table number, unit, year, and population definition.
2. Cross-check a sample of rows against the original source, then audit all values intended for publication.
3. Record extraction decisions and any transformations.
4. Add automated checks for duplicate region-year records, invalid ranges, unexpected missingness, and region-name mismatches.
5. Re-run the manual regression checklist after code changes.
