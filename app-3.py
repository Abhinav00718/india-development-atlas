
import json
import re
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="India Development Atlas",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONFIGURATION
# ============================================================



GEOJSON_URL = (
    "https://raw.githubusercontent.com/"
    "Abhinav00718/india-development-atlas/"
    "main/india_states_ut_simplified.geojson"
)



CACHE_VERSION = "1"

INDICATORS = {
    "Poverty rate (%)": {
        "column": "Poverty_Rate_Percent",
        "unit": "%",
        "description": "Share of the population below a defined poverty threshold.",
        "source": "NITI Aayog / official poverty statistics",
    },
    "Multidimensional poverty (%)": {
        "column": "Multidimensional_Poverty_Percent",
        "unit": "%",
        "description": "Share of the population experiencing multidimensional poverty.",
        "source": "NITI Aayog National Multidimensional Poverty Index",
    },
    "Literacy rate (%)": {
        "column": "Literacy_Rate_Percent",
        "unit": "%",
        "description": "Literacy rate for the relevant population and reference year.",
        "source": "Census of India",
    },
    "GDP per capita (₹)": {
        "column": "GDP_Per_Capita_INR",
        "unit": "₹",
        "description": "Per-capita output. The price basis and year must be documented.",
        "source": "Official state domestic product statistics",
    },
    "Unemployment rate (%)": {
        "column": "Unemployment_Rate_Percent",
        "unit": "%",
        "description": "Unemployment rate for the specified survey definition and period.",
        "source": "Periodic Labour Force Survey",
    },
    "School enrolment (%)": {
        "column": "School_Enrolment_Percent",
        "unit": "%",
        "description": "School enrolment indicator for a specified age group.",
        "source": "UDISE+ / Ministry of Education",
    },
    "Health expenditure per capita (₹)": {
        "column": "Health_Expenditure_Per_Capita_INR",
        "unit": "₹",
        "description": "Per-capita health expenditure using a documented definition.",
        "source": "National Health Accounts / official state data",
    },
}

REGIONS = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
]

ISLAND_REGIONS = {
    "Andaman and Nicobar Islands",
    "Lakshadweep",
}

UT_REGIONS = {
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
}

ALIASES = {
    "orissa": "Odisha",
    "pondicherry": "Puducherry",
    "nct of delhi": "Delhi",
    "national capital territory of delhi": "Delhi",
    "jammu & kashmir": "Jammu and Kashmir",
    "jammu and kashmir": "Jammu and Kashmir",
    "andaman & nicobar islands": "Andaman and Nicobar Islands",
    "andaman and nicobar": "Andaman and Nicobar Islands",
    "dadra and nagar haveli": (
        "Dadra and Nagar Haveli and Daman and Diu"
    ),
    "daman and diu": (
        "Dadra and Nagar Haveli and Daman and Diu"
    ),
    "dadra & nagar haveli and daman & diu": (
        "Dadra and Nagar Haveli and Daman and Diu"
    ),
    "dadra and nagar haveli and daman and diu": (
        "Dadra and Nagar Haveli and Daman and Diu"
    ),
}


# ============================================================
# NAME NORMALISATION
# ============================================================

def clean_name(value):
    """Convert a name to a consistent comparison format."""
    if value is None:
        return ""

    value = str(value).strip().lower()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


REGION_LOOKUP = {
    clean_name(region): region for region in REGIONS
}


def canonical_region(value):
    """Return the official atlas region name where possible."""
    key = clean_name(value)

    if key in REGION_LOOKUP:
        return REGION_LOOKUP[key]

    if key in ALIASES:
        return ALIASES[key]

    # Handle common variants after punctuation normalisation.
    for alias, official_name in ALIASES.items():
        if clean_name(alias) == key:
            return official_name

    return None


# ============================================================
# GEOJSON LOADING AND VALIDATION
# ============================================================

@st.cache_data(show_spinner=False, ttl=86400)
def load_geojson(cache_version=CACHE_VERSION):
    """
    Download and prepare state/UT GeoJSON.

    Returns:
        prepared_geojson: features with properties.atlas_region
        matched_regions: canonical region names found
        missing_regions: expected names not found
        skipped_features: feature names that could not be matched
    """
    response = requests.get(
        GEOJSON_URL,
        timeout=45,
        headers={"User-Agent": "IndiaDevelopmentAtlas/1.0"},
    )
    response.raise_for_status()

    raw = response.json()

    if raw.get("type") != "FeatureCollection":
        raise ValueError(
            "The boundary URL did not return a GeoJSON FeatureCollection."
        )

    features = raw.get("features", [])

    if not features:
        raise ValueError("The GeoJSON file contains no features.")

    prepared_features = []
    matched_regions = set()
    skipped_features = []

    for feature in features:
        properties = feature.get("properties") or {}

        # This repository documents the field as "name".
        # Fallbacks allow for compatible GeoJSON files if the source changes.
        candidate_keys = [
            "name",
            "NAME_1",
            "NAME",
            "ST_NM",
            "shapeName",
            "state_name",
            "STATE",
            "State",
            "admin",
            "state",
        ]

        region_name = None

        for key in candidate_keys:
            if properties.get(key) is not None:
                region_name = canonical_region(properties[key])
                if region_name:
                    break

        if not region_name:
            raw_name = (
                properties.get("name")
                or properties.get("NAME_1")
                or properties.get("NAME")
                or properties.get("shapeName")
                or properties.get("admin")
                or "Unknown feature"
            )
            skipped_features.append(str(raw_name))
            continue

        geometry = feature.get("geometry")

        if not geometry or geometry.get("type") not in {
            "Polygon",
            "MultiPolygon",
        }:
            skipped_features.append(f"{region_name} (invalid geometry)")
            continue

        new_feature = {
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                **properties,
                "atlas_region": region_name,
            },
        }

        prepared_features.append(new_feature)
        matched_regions.add(region_name)

    missing_regions = sorted(set(REGIONS) - matched_regions)

    prepared_geojson = {
        "type": "FeatureCollection",
        "features": prepared_features,
    }

    if not prepared_features:
        raise ValueError(
            "No state or Union Territory names could be matched "
            "in the downloaded GeoJSON."
        )

    return (
        prepared_geojson,
        sorted(matched_regions),
        missing_regions,
        skipped_features,
    )


# ============================================================
# DATASET
# ============================================================

def create_empty_dataset():
    """
    Create a blank data template.

    No development values are fabricated. Add sourced values
    and their reference years when official data is collected.
    """
    rows = []

    for region in REGIONS:
        rows.append(
            {
                "Region": region,
                "Region_Type": (
                    "Union Territory"
                    if region in UT_REGIONS
                    else "State"
                ),
                "Year": None,
                "Poverty_Rate_Percent": None,
                "Multidimensional_Poverty_Percent": None,
                "Literacy_Rate_Percent": None,
                "GDP_Per_Capita_INR": None,
                "Unemployment_Rate_Percent": None,
                "School_Enrolment_Percent": None,
                "Health_Expenditure_Per_Capita_INR": None,
                "Source": None,
                "Notes": None,
            }
        )

    return pd.DataFrame(rows)


def get_dataset():
    """
    Load a user-supplied dataset if present.
    Otherwise return the blank template.
    """
    try:
        uploaded_dataset = st.session_state.get("uploaded_dataset")

        if uploaded_dataset is not None:
            return uploaded_dataset.copy()

    except Exception:
        pass

    return create_empty_dataset()


def validate_dataset(df):
    """Ensure the dataset contains the columns needed by the app."""
    required_columns = [
        "Region",
        "Region_Type",
        "Year",
        *[item["column"] for item in INDICATORS.values()],
        "Source",
        "Notes",
    ]

    for column in required_columns:
        if column not in df.columns:
            df[column] = None

    df["Region"] = df["Region"].apply(canonical_region)
    df = df[df["Region"].notna()].copy()

    # If a region appears more than once, preserve its rows.
    # The map uses the latest available non-missing value.
    return df


def latest_region_values(df, indicator_column):
    """Return one latest non-missing indicator value per region."""
    if df.empty or indicator_column not in df.columns:
        return {}

    data = df.copy()
    data[indicator_column] = pd.to_numeric(
        data[indicator_column], errors="coerce"
    )

    data = data[data[indicator_column].notna()].copy()

    if data.empty:
        return {}

    if "Year" in data.columns:
        data["_year_sort"] = pd.to_numeric(
            data["Year"], errors="coerce"
        )
        data = data.sort_values("_year_sort")

    data = data.drop_duplicates("Region", keep="last")

    return dict(zip(data["Region"], data[indicator_column]))


# ============================================================
# MAP HELPERS
# ============================================================

def filter_geojson(geojson, excluded_regions=None, included_regions=None):
    excluded_regions = excluded_regions or set()

    features = []

    for feature in geojson["features"]:
        name = feature["properties"]["atlas_region"]

        if name in excluded_regions:
            continue

        if included_regions is not None and name not in included_regions:
            continue

        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def make_map(
    geojson,
    dataset,
    selected_indicator,
    selected_region=None,
    island_map=False,
):
    """
    Create a map with a stable geographic frame.

    When indicator data is absent, show a neutral map rather than
    pretending that every region has a score of zero.
    """
    indicator_column = INDICATORS[selected_indicator]["column"]
    values_by_region = latest_region_values(
        dataset, indicator_column
    )

    if island_map:
        map_geojson = filter_geojson(
            geojson,
            included_regions=ISLAND_REGIONS,
        )
        title = "Island territories"
        height = 300
    else:
        map_geojson = filter_geojson(
            geojson,
            excluded_regions=ISLAND_REGIONS,
        )
        title = "States and Union Territories"
        height = 650

    features = map_geojson["features"]

    if not features:
        fig = go.Figure()
        fig.add_annotation(
            text="No geographic features available for this map.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
        return fig, False

    locations = [
        feature["properties"]["atlas_region"]
        for feature in features
    ]

    customdata = []
    z_values = []
    hover_text = []

    for region in locations:
        value = values_by_region.get(region)

        if value is None or pd.isna(value):
            display_value = "No data available"
        else:
            display_value = f"{value:,.2f}"

        customdata.append([display_value])
        hover_text.append(region)

        # Use real indicator values only when present.
        if value is None or pd.isna(value):
            z_values.append(None)
        else:
            z_values.append(float(value))

    has_data = any(value is not None for value in z_values)

    if has_data:
        colorscale = [
            [0.0, "#eff6ff"],
            [0.25, "#bfdbfe"],
            [0.5, "#60a5fa"],
            [0.75, "#2563eb"],
            [1.0, "#1e3a8a"],
        ]
        zmin = min(
            value for value in z_values if value is not None
        )
        zmax = max(
            value for value in z_values if value is not None
        )

        if zmin == zmax:
            zmax = zmin + 1
    else:
        # A neutral colour scale is used until real data is uploaded.
        colorscale = [
            [0.0, "#dbe5f0"],
            [1.0, "#dbe5f0"],
        ]
        z_values = [0 for _ in locations]
        zmin = 0
        zmax = 1

    # Highlight the selected region with a separate boundary trace.
    fig = go.Figure()

    fig.add_trace(
        go.Choropleth(
            geojson=map_geojson,
            featureidkey="properties.atlas_region",
            locations=locations,
            z=z_values,
            zmin=zmin,
            zmax=zmax,
            colorscale=colorscale,
            showscale=has_data,
            colorbar={
                "title": INDICATORS[selected_indicator]["unit"],
                "thickness": 12,
                "len": 0.65,
            } if has_data else None,
            marker={
                "line": {
                    "color": "#ffffff",
                    "width": 1.1,
                }
            },
            customdata=customdata,
            hovertemplate=(
                "<b>%{location}</b><br>"
                + selected_indicator
                + ": %{customdata[0]}"
                + "<extra></extra>"
            ),
            name=title,
        )
    )

    if selected_region and selected_region in locations:
        selected_geojson = filter_geojson(
            map_geojson,
            included_regions={selected_region},
        )

        fig.add_trace(
            go.Choropleth(
                geojson=selected_geojson,
                featureidkey="properties.atlas_region",
                locations=[selected_region],
                z=[1],
                zmin=0,
                zmax=1,
                colorscale=[
                    [0, "#f59e0b"],
                    [1, "#f59e0b"],
                ],
                showscale=False,
                marker={
                    "line": {
                        "color": "#b45309",
                        "width": 2.2,
                    }
                },
                hovertemplate=(
                    "<b>" + selected_region + "</b>"
                    "<extra>Selected region</extra>"
                ),
                name="Selected region",
            )
        )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        showcoastlines=False,
        showcountries=False,
        showland=True,
        landcolor="#f8fafc",
        showocean=False,
        bgcolor="#ffffff",
        projection_type="mercator",
    )

    fig.update_layout(
        title={
            "text": title,
            "x": 0.02,
            "xanchor": "left",
        },
        height=height,
        margin={
            "l": 0,
            "r": 0,
            "t": 55,
            "b": 0,
        },
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={
            "family": "Arial, sans-serif",
            "color": "#0f172a",
        },
        showlegend=False,
    )

    return fig, has_data


# ============================================================
# SIDEBAR AND HEADER
# ============================================================

st.sidebar.title("India Development Atlas")
st.sidebar.caption(
    "Explore development indicators across Indian states and UTs."
)

page = st.sidebar.radio(
    "Navigate",
    [
        "Development Map",
        "Explore a Region",
        "Compare Regions",
        "Data Explorer",
        "About & Sources",
    ],
)

st.sidebar.divider()
st.sidebar.caption(
    "Data values remain blank until official observations are added."
)

st.title("India Development Atlas")
st.write(
    "An interactive platform for exploring socioeconomic "
    "development and regional differences across India."
)


# ============================================================
# LOAD DATA
# ============================================================

try:
    with st.spinner("Loading state and Union Territory boundaries..."):
        (
            geojson,
            matched_regions,
            missing_regions,
            skipped_features,
        ) = load_geojson()

except Exception as error:
    st.error(
        "The boundary file could not be loaded. "
        "The map cannot be displayed until the GeoJSON source is available."
    )
    st.code(str(error))
    st.markdown(
        f"[Open the GeoJSON source]({GEOJSON_URL})"
    )
    st.stop()

dataset = validate_dataset(get_dataset())

# Diagnostic details are useful while verifying all 36 regions.
with st.sidebar.expander("Map diagnostics"):
    st.write(f"GeoJSON features matched: {len(matched_regions)}")
    st.write(f"Expected regions: {len(REGIONS)}")

    if missing_regions:
        st.warning("Regions missing from the boundary file:")
        st.write(", ".join(missing_regions))
    else:
        st.success("All 36 regions were matched.")

    if skipped_features:
        st.caption("Unmatched GeoJSON features:")
        st.write(", ".join(skipped_features))


# ============================================================
# DEVELOPMENT MAP
# ============================================================

if page == "Development Map":
    st.header("Development Map")

    left, right = st.columns([2, 1])

    with right:
        selected_indicator = st.selectbox(
            "Indicator",
            list(INDICATORS.keys()),
        )

        selected_region = st.selectbox(
            "Highlight a region",
            ["None"] + REGIONS,
        )

        if selected_region == "None":
            selected_region = None

        indicator_info = INDICATORS[selected_indicator]

        st.caption(indicator_info["description"])
        st.caption(f"Potential source: {indicator_info['source']}")

    with left:
        fig, has_data = make_map(
            geojson,
            dataset,
            selected_indicator,
            selected_region,
            island_map=False,
        )
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": True, "scrollZoom": True},
        )

    # Island territories have their own enlarged map so they remain visible.
    st.subheader("Island territories")
    st.caption(
        "Enlarged view of Andaman and Nicobar Islands and Lakshadweep. "
        "Their positions are not to the same scale as the mainland map."
    )

    island_fig, _ = make_map(
        geojson,
        dataset,
        selected_indicator,
        selected_region,
        island_map=True,
    )

    st.plotly_chart(
        island_fig,
        use_container_width=True,
        config={"displayModeBar": True, "scrollZoom": True},
    )

    if not has_data:
        st.info(
            "No indicator values have been loaded yet. "
            "The map currently shows boundaries only, not development scores."
        )

    st.download_button(
        "Download data template (CSV)",
        data=create_empty_dataset().to_csv(index=False).encode("utf-8"),
        file_name="india_development_atlas_template.csv",
        mime="text/csv",
    )


# ============================================================
# EXPLORE A REGION
# ============================================================

elif page == "Explore a Region":
    st.header("Explore a Region")

    selected_region = st.selectbox(
        "Choose a state or Union Territory",
        REGIONS,
    )

    region_data = dataset[
        dataset["Region"] == selected_region
    ].copy()

    st.subheader(selected_region)

    region_type = (
        "Union Territory"
        if selected_region in UT_REGIONS
        else "State"
    )

    st.write(f"Administrative category: **{region_type}**")

    if region_data.empty:
        st.info("No observations are available for this region yet.")
    else:
        latest = region_data.iloc[-1]

        for indicator_name, details in INDICATORS.items():
            column = details["column"]
            value = pd.to_numeric(
                pd.Series([latest.get(column)]),
                errors="coerce",
            ).iloc[0]

            if pd.isna(value):
                st.metric(indicator_name, "No data")
            else:
                suffix = details["unit"]
                formatted_value = f"{value:,.2f} {suffix}"
                st.metric(indicator_name, formatted_value)

        st.subheader("Available observations")
        st.dataframe(
            region_data,
            use_container_width=True,
            hide_index=True,
        )

    fig, _ = make_map(
        geojson,
        dataset,
        list(INDICATORS.keys())[0],
        selected_region,
        island_map=selected_region in ISLAND_REGIONS,
    )

    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# COMPARE REGIONS
# ============================================================

elif page == "Compare Regions":
    st.header("Compare Regions")
    st.write(
        "Compare available indicator values across multiple states "
        "and Union Territories."
    )

    selected_regions = st.multiselect(
        "Select regions",
        REGIONS,
        default=["Karnataka", "Tamil Nadu", "Kerala"],
    )

    selected_indicator = st.selectbox(
        "Indicator to compare",
        list(INDICATORS.keys()),
        key="comparison_indicator",
    )

    indicator_column = INDICATORS[selected_indicator]["column"]

    comparison = dataset[
        dataset["Region"].isin(selected_regions)
    ].copy()

    if not comparison.empty:
        comparison[indicator_column] = pd.to_numeric(
            comparison[indicator_column],
            errors="coerce",
        )

        if "Year" in comparison.columns:
            comparison["_year_sort"] = pd.to_numeric(
                comparison["Year"], errors="coerce"
            )
            comparison = comparison.sort_values("_year_sort")

        comparison = comparison.drop_duplicates(
            "Region", keep="last"
        )

        comparison = comparison[
            ["Region", "Region_Type", "Year", indicator_column, "Source"]
        ]

        comparison = comparison.rename(
            columns={indicator_column: selected_indicator}
        )

        st.dataframe(
            comparison,
            use_container_width=True,
            hide_index=True,
        )

        chart_data = comparison.dropna(
            subset=[selected_indicator]
        )

        if not chart_data.empty:
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=chart_data["Region"],
                        y=chart_data[selected_indicator],
                        marker_color="#2563eb",
                    )
                ]
            )

            fig.update_layout(
                title=selected_indicator,
                xaxis_title="Region",
                yaxis_title=INDICATORS[selected_indicator]["unit"],
                height=450,
                margin={"l": 20, "r": 20, "t": 60, "b": 100},
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "There are no numerical observations for this indicator "
                "yet. Upload sourced data to generate a comparison chart."
            )
    else:
        st.info("Select at least one region to compare.")


# ============================================================
# DATA EXPLORER
# ============================================================

elif page == "Data Explorer":
    st.header("Data Explorer")

    st.write(
        "Upload a CSV containing state or Union Territory observations. "
        "The column names in the template should be preserved."
    )

    template = create_empty_dataset()

    st.download_button(
        "Download blank CSV template",
        data=template.to_csv(index=False).encode("utf-8"),
        file_name="india_development_atlas_template.csv",
        mime="text/csv",
    )

    uploaded_file = st.file_uploader(
        "Upload your completed CSV",
        type=["csv"],
    )

    if uploaded_file is not None:
        try:
            uploaded_df = pd.read_csv(uploaded_file)
            uploaded_df = validate_dataset(uploaded_df)

            st.session_state["uploaded_dataset"] = uploaded_df

            st.success(
                f"Loaded {len(uploaded_df)} observation rows. "
                "The data is now being used in this app session."
            )

            st.dataframe(
                uploaded_df,
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "Check units, reference years, definitions and sources "
                "before interpreting or publishing results."
            )

        except Exception as error:
            st.error("The CSV could not be read.")
            st.code(str(error))

    current_dataset = get_dataset()

    st.subheader("Current dataset")
    st.write(f"Rows: {len(current_dataset)}")
    st.write(f"Columns: {len(current_dataset.columns)}")

    st.dataframe(
        current_dataset,
        use_container_width=True,
        hide_index=True,
    )

    csv_bytes = current_dataset.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download current dataset",
        data=csv_bytes,
        file_name="india_development_atlas_data.csv",
        mime="text/csv",
    )


# ============================================================
# ABOUT AND SOURCES
# ============================================================

elif page == "About & Sources":
    st.header("About the India Development Atlas")

    st.write(
        """
        The India Development Atlas is designed to make regional
        socioeconomic differences easier to explore and compare.

        Its purpose is to combine state-level indicators, transparent
        sources, and simple visualisations in one place.
        """
    )

    st.subheader("Data integrity")

    st.write(
        """
        The application does not treat missing values as zero and does
        not invent regional development scores. Every published value
        should be accompanied by a source, reference year, unit and
        indicator definition.
        """
    )

    st.subheader("Potential official data sources")

    sources = [
        (
            "NITI Aayog: National Multidimensional Poverty Index",
            "https://www.niti.gov.in/node/868",
        ),
        (
            "Census of India",
            "https://censusindia.gov.in/census.website/en/data",
        ),
        (
            "Reserve Bank of India: Publications",
            "https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=20658",
        ),
        (
            "UDISE+ school education data",
            "https://www.udiseplus.gov.in/",
        ),
        (
            "Open Government Data Platform India",
            "https://www.data.gov.in/",
        ),
        (
            "GeoJSON boundary repository",
            "https://github.com/iamaanahmad/GeoJson-of-Indian-States",
        ),
    ]

    for label, url in sources:
        st.markdown(f"- [{label}]({url})")

    st.subheader("Map coverage")

    st.write(
        f"Matched regions: {len(matched_regions)} out of {len(REGIONS)}"
    )

    if missing_regions:
        st.warning(
            "The following regions were not matched in the GeoJSON: "
            + ", ".join(missing_regions)
        )
    else:
        st.success(
            "All 28 states and 8 Union Territories were matched by name."
        )

    st.caption(
        "Boundary coverage and legal accuracy should be independently "
        "verified before the map is used for official or policy purposes."
    )
