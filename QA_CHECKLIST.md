# Manual QA Checklist

Run this checklist after each application code change and before describing a new version as stable. It is deliberately focused on regressions in existing functionality.

## Navigation
- [ ] Every expected page appears once in the sidebar.
- [ ] The removed Data Explorer page does not reappear.
- [ ] Economic Relationships Lab appears exactly once.
- [ ] Each page opens without an exception.

## Development Map
- [ ] Each indicator can be selected.
- [ ] Regions with data are coloured.
- [ ] Regions without data remain visible in neutral grey.
- [ ] Hovering a missing-data region says that data is unavailable, not zero.
- [ ] The selected-region highlight still works.
- [ ] The main map geometry and layout look unchanged.

## Island territories
- [ ] Andaman and Nicobar Islands are visible in the island inset.
- [ ] Lakshadweep is visible in the island inset.
- [ ] Both remain visible for an indicator with missing values.
- [ ] Island hover labels correctly distinguish missing data.
- [ ] Island shapes and map layout are unchanged.

## State Rankings
- [ ] Highest-first and lowest-first sorting work.
- [ ] All regions, states-only, and Union-Territories-only filters work.
- [ ] Missing observations are reported separately from ranked observations.
- [ ] CSV export downloads and opens.

## Explore and Compare
- [ ] Explore a Region loads for several states and a Union Territory.
- [ ] Compare Regions works with at least two selected regions.
- [ ] Missing observations do not crash the page.

## Economic Relationships Lab
- [ ] Both axes offer the expected indicators.
- [ ] Region filters work.
- [ ] Scatter plot and correlation render when enough paired observations exist.
- [ ] Reference-year caveat is visible.
- [ ] CSV export downloads and opens.
- [ ] Interpretation does not imply causality.

## Data Quality & Coverage
- [ ] Every indicator appears in the summary.
- [ ] Coverage counts agree with the displayed region-level matrix.
- [ ] Missing data is not counted as zero.
- [ ] Reference years are displayed sensibly.
- [ ] CSV exports download and open.

## About & Sources
- [ ] Source descriptions and limitations are readable.
- [ ] No source is described as fully verified unless it has actually been checked.

## Deployment
- [ ] Streamlit Community Cloud completes deployment.
- [ ] No Python exception is shown in the app.
- [ ] Revisit the Development Map and island inset after any change.
- [ ] Record the change in `CHANGELOG.md` only after the deployed version passes checks.
