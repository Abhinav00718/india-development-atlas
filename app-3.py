
import re
from io import StringIO

import requests
import pandas as pd
import plotly.graph_objects as go
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

GITHUB_RAW = (
    "https://raw.githubusercontent.com/"
    "Abhinav00718/india-development-atlas/main/"
)

GEOJSON_URL = GITHUB_RAW + "india_states_ut_simplified.geojson"
MPI_CSV_URL = GITHUB_RAW + "india_mpi_niti_aayog_2023.csv"
LITERACY_CSV_URL = GITHUB_RAW + "india_literacy_2025.csv"
POVERTY_CSV_URL = GITHUB_RAW + "india_poverty_rate_2011_12.csv"
GSDP_CSV_URL = GITHUB_RAW + "india_gdp_per_capita_gsdp_2019_2024.csv"
UNEMPLOYMENT_CSV_URL = GITHUB_RAW + "india_unemployment_plfs_2025.csv"
SCHOOL_CSV_URL = GITHUB_RAW + "india_school_enrolment_secondary_2024_25.csv"
HEALTH_CSV_URL = GITHUB_RAW + "india_health_expenditure_per_capita_2017_2022.csv"
POWER_CSV_URL = GITHUB_RAW + "india_per_capita_power_availability_2024_25.csv"

INDICATORS = {
    "Poverty rate (%)": {
        "column": "Poverty_Rate_Percent",
        "unit": "%",
        "description": "Combined rural and urban poverty ratio under the Tendulkar methodology for 2011–12; an older estimate.",
        "source": "Press Information Bureau, state-wise poverty estimates for 2011–12 (Tendulkar methodology)",
    },
    "Multidimensional poverty (%)": {
        "column": "Multidimensional_Poverty_Percent",
        "unit": "%",
        "description": "Share of the population experiencing multidimensional poverty.",
        "source": "NITI Aayog National Multidimensional Poverty Index, 2023",
    },
    "Literacy rate (%)": {
        "column": "Literacy_Rate_Percent",
        "unit": "%",
        "description": "Literacy rate for the relevant population and reference year.",
        "source": "MoSPI, PLFS Annual Report 2025",
    },
    "Per-capita GSDP (₹)": {
        "column": "GDP_Per_Capita_INR",
        "unit": "₹",
        "description": "Gross state domestic product per person at current prices; fiscal year is labelled by its ending year.",
        "source": "MoSPI / State DES; Rajya Sabha Unstarred Question 1677 (10 Dec 2024)",
    },
    "Unemployment rate (%)": {
        "column": "Unemployment_Rate_Percent",
        "unit": "%",
        "description": "Usual-status (ps+ss) unemployment rate, all ages, rural and urban persons, PLFS 2025.",
        "source": "MoSPI, PLFS Annual Report 2025, Appendix A Table 18.0",
    },
    "School enrolment (%)": {
        "column": "School_Enrolment_Percent",
        "unit": "%",
        "description": "Gross enrolment ratio at secondary level (Classes IX–X), UDISE+ 2024–25; GER can exceed 100%.",
        "source": "UDISE+ 2024–25; values reproduced in PRS Education analysis",
    },
    "Health expenditure per capita (₹)": {
        "column": "Health_Expenditure_Per_Capita_INR",
        "unit": "₹",
        "description": "Per-capita total government health expenditure (₹); fiscal year is labelled by its ending year.",
        "source": "National Health Accounts; Rajya Sabha Unstarred Question 276 (4 Feb 2025)",
    },
    "Per-capita power availability (kWh)": {
        "column": "Per_Capita_Power_Availability_kWh",
        "unit": "kWh per person",
        "description": "Per-capita availability of power for fiscal year 2024–25. This is an availability measure, not household electricity consumption. The Ladakh value is unavailable in the source table.",
        "source": "RBI, Handbook of Statistics on Indian States, Table 138; Dataful dataset 21005",
    },
}

REGIONS = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chhattisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
    "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
    "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]

ISLAND_REGIONS = {"Andaman and Nicobar Islands", "Lakshadweep"}

UT_REGIONS = {
    "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
}

ALIASES = {
    "orissa": "Odisha",
    "pondicherry": "Puducherry",
    "nct of delhi": "Delhi",
    "national capital territory of delhi": "Delhi",
    "jammu & kashmir": "Jammu and Kashmir",
    "andaman & nicobar islands": "Andaman and Nicobar Islands",
    "andaman and nicobar": "Andaman and Nicobar Islands",
    "dadra and nagar haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "dadra & nagar haveli and daman & diu":
        "Dadra and Nagar Haveli and Daman and Diu",
}

NAME_FIELD_CANDIDATES = [
    "atlas_region", "ST_NM", "STATE", "State", "state", "NAME_1",
    "NAME", "name", "admin", "state_name", "ShapeName", "st_nm",
    "STNAME", "state_ut", "State_UT", "State/UT",
]


# ============================================================
# REGION NAME HELPERS
# ============================================================

def clean_name(value):
    if value is None:
        return ""
    value = str(value).strip().lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


REGION_LOOKUP = {clean_name(region): region for region in REGIONS}


def canonical_region(value):
    key = clean_name(value)

    if key in REGION_LOOKUP:
        return REGION_LOOKUP[key]

    for alias, official_name in ALIASES.items():
        if clean_name(alias) == key:
            return official_name

    return None


# ============================================================
# DATASET AND CSV TEMPLATE
# ============================================================

def create_empty_dataset():
    rows = []

    for region in REGIONS:
        rows.append({
            "Region": region,
            "Region_Type": (
                "Union Territory" if region in UT_REGIONS else "State"
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
        })

    return pd.DataFrame(rows)


def validate_dataset(df):
    required_columns = [
        "Region",
        "Region_Type",
        "Year",
        *[indicator["column"] for indicator in INDICATORS.values()],
        "Source",
        "Notes",
    ]

    df = df.copy()

    for column in required_columns:
        if column not in df.columns:
            df[column] = None

    df["Region"] = df["Region"].apply(canonical_region)
    df = df[df["Region"].notna()].copy()

    # Ensure numeric fields are numeric, while preserving missing values.
    for column in ["Year"] + [
        indicator["column"] for indicator in INDICATORS.values()
    ]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


@st.cache_data(show_spinner="Loading MPI data from GitHub...", ttl=3600)
def load_mpi_dataset():
    """Download and validate the committed MPI CSV from GitHub."""
    response = requests.get(MPI_CSV_URL, timeout=30)
    response.raise_for_status()

    df = pd.read_csv(StringIO(response.text))

    if "Multidimensional_Poverty_Percent" not in df.columns:
        raise ValueError(
            "The CSV is missing the Multidimensional_Poverty_Percent column."
        )

    df = validate_dataset(df)

    if df.empty:
        raise ValueError(
            "The MPI CSV was downloaded, but no recognised regions were found."
        )

    return df

@st.cache_data(show_spinner="Loading PLFS 2025 literacy data...", ttl=3600)
def load_literacy_dataset():
    response = requests.get(LITERACY_CSV_URL, timeout=30)
    response.raise_for_status()

    df = pd.read_csv(StringIO(response.text))

    if "Literacy_Rate_Percent" not in df.columns:
        raise ValueError("Literacy CSV is missing Literacy_Rate_Percent.")

    df = validate_dataset(df)
    df = df.dropna(subset=["Year", "Literacy_Rate_Percent"])

    if df.empty:
        raise ValueError("No valid literacy observations were found.")

    return df


@st.cache_data(show_spinner="Loading indicator data from GitHub...", ttl=3600)
def load_indicator_csv(url, indicator_column, label):
    """Load one indicator's dedicated CSV and preserve genuinely missing values."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    df = pd.read_csv(StringIO(response.text))

    if indicator_column not in df.columns:
        raise ValueError(f"The {label} CSV is missing {indicator_column}.")

    df = validate_dataset(df)
    df = df.dropna(subset=["Year", indicator_column])

    if df.empty:
        raise ValueError(f"No valid dated observations were found for {label}.")

    return df


def get_indicator_dataset(indicator_name):
    uploaded = st.session_state.get("uploaded_dataset")

    if uploaded is not None:
        return validate_dataset(uploaded.copy())

    if indicator_name == "Multidimensional poverty (%)":
        return dataset

    indicator_sources = {
        "Poverty rate (%)": (
            POVERTY_CSV_URL, "Poverty_Rate_Percent", "poverty",
        ),
        "Literacy rate (%)": (
            LITERACY_CSV_URL, "Literacy_Rate_Percent", "literacy",
        ),
        "Per-capita GSDP (₹)": (
            GSDP_CSV_URL, "GDP_Per_Capita_INR", "per-capita GSDP",
        ),
        "Unemployment rate (%)": (
            UNEMPLOYMENT_CSV_URL, "Unemployment_Rate_Percent", "unemployment",
        ),
        "School enrolment (%)": (
            SCHOOL_CSV_URL, "School_Enrolment_Percent", "school enrolment",
        ),
        "Health expenditure per capita (₹)": (
            HEALTH_CSV_URL, "Health_Expenditure_Per_Capita_INR",
            "health expenditure",
        ),
        "Per-capita power availability (kWh)": (
            POWER_CSV_URL, "Per_Capita_Power_Availability_kWh",
            "per-capita power availability",
        ),
    }

    if indicator_name not in indicator_sources:
        return dataset

    url, column, label = indicator_sources[indicator_name]
    try:
        return load_indicator_csv(url, column, label)
    except Exception as error:
        st.error(f"Could not load the {label} dataset from GitHub.")
        st.caption(str(error))
        return create_empty_dataset()


def get_dataset():
    """Uploaded session data takes priority; otherwise load GitHub MPI data."""
    uploaded = st.session_state.get("uploaded_dataset")

    if uploaded is not None:
        return validate_dataset(uploaded.copy())

    try:
        return load_mpi_dataset()
    except Exception as error:
        st.error(
            "The MPI dataset could not be loaded from GitHub. "
            "Check the CSV filename, repository, and main branch."
        )
        st.caption(str(error))
        return create_empty_dataset()


def latest_region_values(df, indicator_column):
    """Return the latest available numeric observation for each region."""
    if df.empty or indicator_column not in df.columns:
        return {}

    data = df.copy()
    data[indicator_column] = pd.to_numeric(
        data[indicator_column], errors="coerce"
    )
    data["Year"] = pd.to_numeric(data["Year"], errors="coerce")
    data = data.dropna(subset=[indicator_column, "Year"])

    if data.empty:
        return {}

    data = data.sort_values("Year")
    data = data.drop_duplicates("Region", keep="last")

    return dict(zip(data["Region"], data[indicator_column]))


# ============================================================
# GEOJSON LOADING
# ============================================================

@st.cache_data(show_spinner="Loading India state boundaries...", ttl=86400)
def load_geojson():
    response = requests.get(GEOJSON_URL, timeout=60)
    response.raise_for_status()
    raw = response.json()

    if raw.get("type") != "FeatureCollection":
        raise ValueError("The boundary file is not a GeoJSON FeatureCollection.")

    features = raw.get("features", [])

    if not features:
        raise ValueError("The GeoJSON file contains no features.")

    available_properties = set()
    for feature in features:
        available_properties.update(
            (feature.get("properties") or {}).keys()
        )

    name_field = next(
        (field for field in NAME_FIELD_CANDIDATES
         if field in available_properties),
        None,
    )

    if name_field is None:
        raise ValueError(
            f"Could not identify the region-name field. "
            f"Properties found: {sorted(available_properties)}"
        )

    prepared_features = []
    matched_regions = set()
    skipped_features = []

    for feature in features:
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry")
        region = canonical_region(properties.get(name_field))

        if region is None:
            skipped_features.append(str(properties.get(name_field, "Unknown")))
            continue

        if not geometry or geometry.get("type") not in (
            "Polygon", "MultiPolygon"
        ):
            skipped_features.append(f"{region}: missing/unsupported geometry")
            continue

        prepared_features.append({
            "type": "Feature",
            "geometry": geometry,
            "properties": {**properties, "atlas_region": region},
        })
        matched_regions.add(region)

    if not prepared_features:
        raise ValueError("No state or Union Territory boundaries were matched.")

    prepared_geojson = {
        "type": "FeatureCollection",
        "features": prepared_features,
    }

    missing_regions = sorted(set(REGIONS) - matched_regions)

    return (
        prepared_geojson,
        sorted(matched_regions),
        missing_regions,
        skipped_features,
        name_field,
        len(features),
    )


# ============================================================
# MAP HELPERS
# ============================================================

def filter_geojson(geojson, excluded_regions=None, included_regions=None):
    excluded_regions = excluded_regions or set()
    selected_features = []

    for feature in geojson["features"]:
        name = feature["properties"]["atlas_region"]

        if name in excluded_regions:
            continue

        if included_regions is not None and name not in included_regions:
            continue

        selected_features.append(feature)

    return {"type": "FeatureCollection", "features": selected_features}


def make_map(
    geojson,
    dataset,
    selected_indicator,
    selected_region=None,
    island_map=False,
):
    indicator_column = INDICATORS[selected_indicator]["column"]
    unit = INDICATORS[selected_indicator]["unit"]
    values_by_region = latest_region_values(dataset, indicator_column)

    if island_map:
        map_geojson = filter_geojson(
            geojson, included_regions=ISLAND_REGIONS
        )
        map_title = "Island territories"
        height = 330
    else:
        map_geojson = filter_geojson(
            geojson, excluded_regions=ISLAND_REGIONS
        )
        map_title = "India: states and Union Territories"
        height = 680

    features = map_geojson["features"]
    fig = go.Figure()

    if not features:
        fig.add_annotation(
            text="No geographic features available for this view.",
            x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
        )
        fig.update_layout(height=height)
        return fig, False

    locations = [
        feature["properties"]["atlas_region"] for feature in features
    ]
    actual_values = [values_by_region.get(region) for region in locations]

    has_data = any(
        value is not None and pd.notna(value) for value in actual_values
    )

    if has_data:
        z_values = [
            float(value) if value is not None and pd.notna(value) else None
            for value in actual_values
        ]
        valid_values = [value for value in z_values if value is not None]
        zmin, zmax = min(valid_values), max(valid_values)

        if zmin == zmax:
            zmax = zmin + 1

        colorscale = [
            [0.0, "#eff6ff"],
            [0.25, "#bfdbfe"],
            [0.5, "#60a5fa"],
            [0.75, "#2563eb"],
            [1.0, "#1e3a8a"],
        ]
    else:
        z_values = [0] * len(locations)
        zmin, zmax = 0, 1
        colorscale = [[0.0, "#d3deea"], [1.0, "#d3deea"]]

    customdata = [
        [
            f"{value:,.2f} {unit}"
            if value is not None and pd.notna(value)
            else "No data available"
        ]
        for value in actual_values
    ]

    fig.add_trace(go.Choropleth(
        geojson=map_geojson,
        featureidkey="properties.atlas_region",
        locations=locations,
        z=z_values,
        zmin=zmin,
        zmax=zmax,
        colorscale=colorscale,
        showscale=has_data,
        colorbar={"title": unit, "thickness": 14, "len": 0.65}
        if has_data else None,
        marker={"line": {"color": "#ffffff", "width": 1.0}},
        customdata=customdata,
        hovertemplate=(
            "<b>%{location}</b><br>"
            + selected_indicator
            + ": %{customdata[0]}<extra></extra>"
        ),
        name=map_title,
    ))

    if selected_region and selected_region in locations:
        selected_geojson = filter_geojson(
            map_geojson, included_regions={selected_region}
        )

        fig.add_trace(go.Choropleth(
            geojson=selected_geojson,
            featureidkey="properties.atlas_region",
            locations=[selected_region],
            z=[1],
            zmin=0,
            zmax=1,
            colorscale=[[0, "#f59e0b"], [1, "#f59e0b"]],
            showscale=False,
            marker={"line": {"color": "#92400e", "width": 2.2}},
            hovertemplate=(
                "<b>" + selected_region + "</b><extra>Selected region</extra>"
            ),
            name="Selected region",
        ))

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
        title={"text": map_title, "x": 0.02, "xanchor": "left"},
        height=height,
        margin={"l": 0, "r": 0, "t": 55, "b": 0},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"family": "Arial, sans-serif", "color": "#0f172a"},
        showlegend=False,
    )

    return fig, has_data


# ============================================================
# SIDEBAR, HEADER, AND INITIAL DATA
# ============================================================

st.sidebar.title("India Development Atlas")
st.sidebar.caption(
    "Explore socioeconomic development across Indian states and UTs."
)

page = st.sidebar.radio(
    "Navigate",
    [
        "Development Map",
        "State Rankings",
        "Explore a Region",
        "Compare Regions",
        "Data Explorer",
        "About & Sources",
    ],
)

st.sidebar.divider()
st.sidebar.caption(
    "Each indicator is loaded from its own CSV in the GitHub repository. "
    "Some sources are older or have missing regional values."
)

st.title("India Development Atlas")
st.write(
    "An interactive platform for exploring socioeconomic development "
    "and regional differences across India."
)

try:
    (
        geojson,
        matched_regions,
        missing_regions,
        skipped_features,
        name_field,
        original_feature_count,
    ) = load_geojson()
except Exception as error:
    st.error("The boundary file could not be loaded.")
    st.markdown(f"[Open the GeoJSON URL]({GEOJSON_URL})")
    st.caption(
        "Check that the file is in the root of the main branch "
        "and that the URL opens raw GeoJSON."
    )
    st.code(str(error))
    st.stop()

dataset = validate_dataset(get_dataset())

with st.sidebar.expander("Map diagnostics"):
    st.write(f"Source features: {original_feature_count}")
    st.write(f"Matched regions: {len(matched_regions)} / 36")
    st.write(f"Name field: `{name_field}`")

    if missing_regions:
        st.warning("Regions not matched:")
        st.write(", ".join(missing_regions))
    else:
        st.success("All 36 expected regions were matched.")

    if skipped_features:
        st.caption("Skipped features:")
        st.write(", ".join(skipped_features))


# ============================================================
# PAGE 1: DEVELOPMENT MAP
# ============================================================

if page == "Development Map":
    st.header("Development Map")

    left, right = st.columns([2.2, 1])

    with right:
        selected_indicator = st.selectbox(
            "Select indicator", list(INDICATORS.keys())
        )
        selected_region = st.selectbox(
            "Highlight a region", ["None"] + REGIONS
        )
        if selected_region == "None":
            selected_region = None

        indicator_info = INDICATORS[selected_indicator]
        indicator_dataset = get_indicator_dataset(selected_indicator)
        st.caption(indicator_info["description"])
        st.caption(f"Source: {indicator_info['source']}")

    with left:
        fig, has_data = make_map(
    geojson, indicator_dataset, selected_indicator, selected_region
)
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": True, "scrollZoom": True},
        )

    st.subheader("Island territories")
    st.caption(
        "Enlarged view of Andaman and Nicobar Islands and Lakshadweep. "
        "This inset is not to the same geographic scale as mainland India."
    )

    island_fig, _ = make_map(
        geojson,
        indicator_dataset,
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
            "No values are available for this indicator yet. "
            "Regions are shown in a neutral colour."
        )
    elif selected_indicator == "Multidimensional poverty (%)":
        st.caption(
            "MPI values compare NFHS-4 (2015–16) with NFHS-5 (2019–21). "
            "The app uses 2021 as a sortable label for the 2019–21 survey "
            "period, not as a single-year estimate."
        )

    st.download_button(
        "Download blank CSV template",
        data=create_empty_dataset().to_csv(index=False).encode("utf-8"),
        file_name="india_development_atlas_template.csv",
        mime="text/csv",
    )



# ============================================================
# PAGE 2: STATE RANKINGS
# ============================================================

elif page == "State Rankings":
    st.header("State Development Rankings")
    st.write(
        "Rank states and Union Territories on a selected development indicator. "
        "Each region uses its latest available observation in that indicator's source."
    )

    controls = st.columns([1.6, 1, 1])
    with controls[0]:
        selected_indicator = st.selectbox(
            "Indicator to rank",
            list(INDICATORS.keys()),
            key="ranking_indicator",
        )
    with controls[1]:
        region_scope = st.selectbox(
            "Regions to include",
            ["All regions", "States only", "Union Territories only"],
            key="ranking_scope",
        )
    with controls[2]:
        ranking_order = st.selectbox(
            "Ranking order",
            ["Highest first", "Lowest first"],
            key="ranking_order",
            help=(
                "Choose whether higher or lower values appear first. "
                "The meaning of 'better' depends on the indicator."
            ),
        )

    details = INDICATORS[selected_indicator]
    indicator_column = details["column"]
    ranking_dataset = get_indicator_dataset(selected_indicator).copy()

    ranking_dataset["Year"] = pd.to_numeric(
        ranking_dataset["Year"], errors="coerce"
    )
    ranking_dataset[indicator_column] = pd.to_numeric(
        ranking_dataset[indicator_column], errors="coerce"
    )
    ranking_dataset = ranking_dataset.dropna(subset=["Year"])
    ranking_dataset = ranking_dataset.sort_values("Year")
    ranking_dataset = ranking_dataset.drop_duplicates("Region", keep="last")

    # Start from all 36 regions so missing observations remain visible.
    rankings = pd.DataFrame({"Region": REGIONS})
    rankings["Region_Type"] = rankings["Region"].apply(
        lambda region: "Union Territory" if region in UT_REGIONS else "State"
    )
    rankings = rankings.merge(
        ranking_dataset[["Region", "Year", indicator_column, "Source", "Notes"]],
        on="Region",
        how="left",
    )
    rankings["Reference year"] = rankings["Year"].apply(
        lambda year: int(year) if pd.notna(year) else None
    )
    rankings["Data status"] = rankings[indicator_column].apply(
        lambda value: "Available" if pd.notna(value) else "Unavailable"
    )

    if region_scope == "States only":
        rankings = rankings[rankings["Region_Type"] == "State"].copy()
    elif region_scope == "Union Territories only":
        rankings = rankings[rankings["Region_Type"] == "Union Territory"].copy()

    available = rankings.dropna(subset=[indicator_column]).copy()
    unavailable = rankings[rankings[indicator_column].isna()].copy()
    ascending = ranking_order == "Lowest first"
    available = available.sort_values(
        indicator_column, ascending=ascending
    ).reset_index(drop=True)
    available.insert(0, "Rank", range(1, len(available) + 1))

    total_regions = len(rankings)
    available_count = len(available)
    missing_count = len(unavailable)
    metric_cols = st.columns(3)
    metric_cols[0].metric("Regions included", total_regions)
    metric_cols[1].metric("Regions with data", f"{available_count} / {total_regions}")
    metric_cols[2].metric("Regions missing data", missing_count)

    st.caption(details["description"])
    st.caption(f"Source: {details['source']} · Unit: {details['unit']}")
    st.info(
        "Rank order is numerical, not a judgement of overall development. "
        "For poverty and unemployment, for example, a lower value may be preferable; "
        "for income or power availability, interpretation is different. "
        "Reference years may differ across regions."
    )

    display_columns = [
        "Rank", "Region", "Region_Type", indicator_column,
        "Reference year", "Data status",
    ]
    display = available[display_columns].rename(columns={
        "Region_Type": "Region type",
        indicator_column: f"{selected_indicator} ({details['unit']})",
    })

    st.subheader("Ranked regions")
    if display.empty:
        st.warning("No valid observations are available for this indicator and filter.")
    else:
        st.dataframe(
            display.round({f"{selected_indicator} ({details['unit']})": 2}),
            use_container_width=True,
            hide_index=True,
        )

        chart_data = available.head(15).sort_values(
            indicator_column, ascending=True
        )
        fig = go.Figure(go.Bar(
            x=chart_data[indicator_column],
            y=chart_data["Region"],
            orientation="h",
            text=chart_data[indicator_column].map(lambda value: f"{value:,.2f}"),
            textposition="outside",
            cliponaxis=False,
            customdata=chart_data[["Reference year"]].to_numpy(),
            hovertemplate=(
                "<b>%{y}</b><br>"
                + selected_indicator + ": %{x:,.2f} " + details["unit"]
                + "<br>Reference year: %{customdata[0]}<extra></extra>"
            ),
        ))
        fig.update_layout(
            title=f"Top {min(15, len(available))} by selected ranking order",
            xaxis_title=f"{selected_indicator} ({details['unit']})",
            yaxis_title="",
            template="plotly_white",
            height=max(420, 28 * min(15, len(available)) + 140),
            margin={"l": 150, "r": 70, "t": 70, "b": 60},
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Regions with unavailable data")
    if unavailable.empty:
        st.success("All regions in this selection have a valid observation.")
    else:
        st.dataframe(
            unavailable[["Region", "Region_Type", "Data status"]].rename(
                columns={"Region_Type": "Region type"}
            ),
            use_container_width=True,
            hide_index=True,
        )

    export = rankings[[
        "Region", "Region_Type", indicator_column,
        "Reference year", "Data status", "Source", "Notes",
    ]].rename(columns={
        "Region_Type": "Region type",
        indicator_column: f"{selected_indicator} ({details['unit']})",
    })
    st.download_button(
        "Download ranking and data coverage (CSV)",
        data=export.to_csv(index=False).encode("utf-8"),
        file_name="india_development_rankings.csv",
        mime="text/csv",
    )


# ============================================================
# PAGE 2: EXPLORE A REGION
# ============================================================

elif page == "Explore a Region":
    st.header("Explore a Region")
    selected_region = st.selectbox("Choose a state or UT", REGIONS)

    region_type = (
        "Union Territory" if selected_region in UT_REGIONS else "State"
    )
    st.subheader(selected_region)
    st.write(f"Administrative category: **{region_type}**")

    st.caption(
        "Each metric uses the latest available observation in its own source. "
        "Reference years may differ, so values are not necessarily from the same year."
    )

    cols = st.columns(2)
    for i, (indicator_name, details) in enumerate(INDICATORS.items()):
        indicator_dataset = get_indicator_dataset(indicator_name)
        region_rows = indicator_dataset[
            indicator_dataset["Region"] == selected_region
        ].copy()

        if not region_rows.empty:
            region_rows["Year"] = pd.to_numeric(
                region_rows["Year"], errors="coerce"
            )
            region_rows[details["column"]] = pd.to_numeric(
                region_rows[details["column"]], errors="coerce"
            )
            region_rows = region_rows.dropna(
                subset=["Year", details["column"]]
            ).sort_values("Year")

        if region_rows.empty:
            cols[i % 2].metric(indicator_name, "No data")
        else:
            latest = region_rows.iloc[-1]
            value = latest[details["column"]]
            year = int(latest["Year"])
            cols[i % 2].metric(
                indicator_name,
                f"{value:,.2f} {details['unit']}",
                help=f"Reference year: {year}. Source: {details['source']}",
            )
            cols[i % 2].caption(f"{indicator_name}: reference year {year}")


    fig, _ = make_map(
        geojson,
        dataset,
        "Multidimensional poverty (%)",
        selected_region,
        island_map=selected_region in ISLAND_REGIONS,
    )
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# PAGE 3: COMPARE REGIONS
# ============================================================


# ============================================================
# PAGE 3: COMPARE REGIONS
# ============================================================

elif page == "Compare Regions":
    st.header("Compare Regions")

    selected_regions = st.multiselect(
        "Choose regions",
        REGIONS,
        default=["Karnataka", "Tamil Nadu", "Kerala"],
    )

    selected_indicator = st.selectbox(
        "Indicator to compare",
        list(INDICATORS.keys()),
        key="comparison_indicator",
    )

    indicator_column = INDICATORS[selected_indicator]["column"]
    comparison_dataset = get_indicator_dataset(selected_indicator)

    comparison = comparison_dataset[
     comparison_dataset["Region"].isin(selected_regions)
    ].copy()
    if not comparison.empty:
        comparison["Year"] = pd.to_numeric(
            comparison["Year"], errors="coerce"
        )
        comparison[indicator_column] = pd.to_numeric(
            comparison[indicator_column], errors="coerce"
        )

        comparison = comparison.dropna(subset=["Year"])
        comparison = comparison.sort_values("Year")
        comparison = comparison.drop_duplicates("Region", keep="last")

        display = comparison[
            ["Region", "Region_Type", "Year", indicator_column, "Source"]
        ].rename(columns={indicator_column: selected_indicator})

        st.subheader("Latest available indicator values")
        st.dataframe(display, use_container_width=True, hide_index=True)

        chart_data = comparison.dropna(subset=[indicator_column])

        if not chart_data.empty:
            fig = go.Figure(go.Bar(
                x=chart_data["Region"],
                y=chart_data[indicator_column],
                text=chart_data[indicator_column].map(lambda x: f"{x:.2f}"),
                textposition="outside",
                cliponaxis=False,
            ))
            fig.update_layout(
                title=selected_indicator,
                xaxis_title="Region",
                yaxis_title=INDICATORS[selected_indicator]["unit"],
                template="plotly_white",
                height=450,
                margin={"l": 30, "r": 60, "t": 60, "b": 100},
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select one or more regions to compare.")

    # --------------------------------------------------------
    # MPI POVERTY REDUCTION ANALYSIS
    # --------------------------------------------------------

    st.divider()
    st.header("Multidimensional Poverty: Change Over Time")
    st.caption(
        "Source: NITI Aayog, India National Multidimensional Poverty "
        "Index: A Progress Review 2023. NFHS-4 covers 2015–16; "
        "NFHS-5 covers 2019–21. These are survey periods, not annual estimates."
    )

    mpi_col = "Multidimensional_Poverty_Percent"
    mpi_data = dataset.copy()

    mpi_data["Year"] = pd.to_numeric(mpi_data["Year"], errors="coerce")
    mpi_data[mpi_col] = pd.to_numeric(
        mpi_data[mpi_col], errors="coerce"
    )

    mpi_data = mpi_data[
        mpi_data["Year"].isin([2016, 2021])
    ].dropna(subset=["Region", "Year", mpi_col])

    if mpi_data.empty:
        st.warning(
            "The current dataset has no usable MPI survey-period data. "
            "In Data Explorer, remove any uploaded CSV to return to the "
            "default GitHub dataset."
        )
    else:
        mpi = mpi_data.pivot_table(
            index="Region",
            columns="Year",
            values=mpi_col,
            aggfunc="first",
        ).reset_index()

        mpi = mpi.rename(columns={
            2016: "MPI_Poverty_2015_16",
            2021: "MPI_Poverty_2019_21",
        })

        required = ["MPI_Poverty_2015_16", "MPI_Poverty_2019_21"]

        if not all(col in mpi.columns for col in required):
            st.warning("Both survey periods are needed for this comparison.")
        else:
            mpi = mpi.dropna(subset=required).copy()

            mpi["Region_Type"] = mpi["Region"].apply(
                lambda r: "Union Territory" if r in UT_REGIONS else "State"
            )

            mpi["Reduction_Percentage_Points"] = (
                mpi["MPI_Poverty_2015_16"] -
                mpi["MPI_Poverty_2019_21"]
            )

            mpi["Relative_Reduction_Percent"] = (
                mpi["Reduction_Percentage_Points"] /
                mpi["MPI_Poverty_2015_16"].replace(0, float("nan"))
            ) * 100

            # 1. Summary metrics
            ranked = mpi.sort_values(
                "Reduction_Percentage_Points",
                ascending=False,
            ).reset_index(drop=True)

            ranked.insert(0, "Rank", ranked.index + 1)

            largest = ranked.iloc[0]
            lowest_final = mpi.loc[
                mpi["MPI_Poverty_2019_21"].idxmin()
            ]

            c1, c2, c3 = st.columns(3)
            c1.metric("Regions compared", f"{len(mpi)} / 36")
            c2.metric(
                "Largest reduction",
                f"{largest['Reduction_Percentage_Points']:.2f} pp",
                largest["Region"],
            )
            c3.metric(
                "Lowest poverty in 2019–21",
                f"{lowest_final['MPI_Poverty_2019_21']:.2f}%",
                lowest_final["Region"],
            )

            # 2. Full ranking table
            st.subheader("1. Poverty reduction rankings")

            ranking_display = ranked[[
                "Rank",
                "Region",
                "Region_Type",
                "MPI_Poverty_2015_16",
                "MPI_Poverty_2019_21",
                "Reduction_Percentage_Points",
                "Relative_Reduction_Percent",
            ]].rename(columns={
                "MPI_Poverty_2015_16": "Poverty 2015–16 (%)",
                "MPI_Poverty_2019_21": "Poverty 2019–21 (%)",
                "Reduction_Percentage_Points": "Reduction (percentage points)",
                "Relative_Reduction_Percent": "Relative reduction (%)",
            })

            st.dataframe(
                ranking_display.round(2),
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "Download MPI rankings as CSV",
                data=ranking_display.round(2).to_csv(index=False).encode("utf-8"),
                file_name="india_mpi_poverty_reduction_rankings.csv",
                mime="text/csv",
            )

            # 3. Chart: largest reductions
            st.subheader("2. Ten largest poverty reductions")

            top10 = ranked.head(10).sort_values(
                "Reduction_Percentage_Points",
                ascending=True,
            )

            fig = go.Figure(go.Bar(
                x=top10["Reduction_Percentage_Points"],
                y=top10["Region"],
                orientation="h",
                text=top10["Reduction_Percentage_Points"].map(
                    lambda x: f"{x:.2f} pp"
                ),
                textposition="outside",
                cliponaxis=False,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Reduction: %{x:.2f} percentage points"
                    "<extra></extra>"
                ),
            ))

            fig.update_layout(
                title="Largest Reductions in MPI Poverty, 2015–16 to 2019–21",
                xaxis_title="Reduction (percentage points)",
                yaxis_title="",
                template="plotly_white",
                height=500,
                margin={"l": 190, "r": 100, "t": 80, "b": 60},
            )

            st.plotly_chart(fig, use_container_width=True)

            # 4. Before-and-after chart
            st.subheader("3. Compare survey periods")

            defaults = [
                r for r in ["Bihar", "Karnataka", "Tamil Nadu"]
                if r in set(mpi["Region"])
            ]

            chosen = st.multiselect(
                "Choose regions for the before-and-after chart",
                options=sorted(mpi["Region"].tolist()),
                default=defaults,
                key="mpi_period_regions",
            )

            period = mpi[mpi["Region"].isin(chosen)].copy()

            if not period.empty:
                period = period.sort_values(
                    "MPI_Poverty_2019_21", ascending=False
                )

                fig = go.Figure()

                fig.add_trace(go.Bar(
                    y=period["Region"],
                    x=period["MPI_Poverty_2015_16"],
                    name="NFHS-4 (2015–16)",
                    orientation="h",
                    text=period["MPI_Poverty_2015_16"].map(
                        lambda x: f"{x:.2f}%"
                    ),
                    textposition="outside",
                    cliponaxis=False,
                ))

                fig.add_trace(go.Bar(
                    y=period["Region"],
                    x=period["MPI_Poverty_2019_21"],
                    name="NFHS-5 (2019–21)",
                    orientation="h",
                    text=period["MPI_Poverty_2019_21"].map(
                        lambda x: f"{x:.2f}%"
                    ),
                    textposition="outside",
                    cliponaxis=False,
                ))

                max_value = period[required].max().max()

                         
                fig.update_layout(
                    title="MPI Poverty Rates by Survey Period",
                    yaxis_title="",
                    barmode="group",
                    template="plotly_white",
                    height=max(420, 100 + 55 * len(period)),
                    margin={"l": 180, "r": 100, "t": 80, "b": 210},
                    legend={
                        "title": {"text": ""},
                        "orientation": "h",
                        "yanchor": "top",
                        "y": -0.50,
                        "xanchor": "center",
                        "x": 0.5,
                    },
                )

                fig.update_xaxes(
                    title_text="Population in multidimensional poverty (%)",
                    title_standoff=18,
                    range=[0, max(10, float(max_value) * 1.25)]
                )


                fig.update_xaxes(
                    range=[0, max(10, float(max_value) * 1.25)]
                )
                fig.update_layout(legend_title_text=None)
                st.plotly_chart(fig, use_container_width=True)

            st.caption(
                "Percentage-point reduction = initial rate minus final rate. "
                "Relative reduction is a separate measure calculated as "
                "(initial rate − final rate) / initial rate × 100. "
                "A smaller reduction does not automatically mean worse "
                "performance, because regions started at different poverty levels."
            )



# ============================================================
# PAGE 4: DATA EXPLORER
# ============================================================

elif page == "Data Explorer":
    st.header("Data Explorer")
    st.write(
        "Upload a CSV of state or Union Territory observations. "
        "Use the template to preserve the expected column names."
    )

    st.download_button(
        "Download blank CSV template",
        data=create_empty_dataset().to_csv(index=False).encode("utf-8"),
        file_name="india_development_atlas_template.csv",
        mime="text/csv",
    )

    uploaded_file = st.file_uploader(
        "Upload completed CSV", type=["csv"]
    )

    if uploaded_file is not None:
        try:
            uploaded_df = pd.read_csv(uploaded_file)
            uploaded_df = validate_dataset(uploaded_df)

            if uploaded_df.empty:
                st.error(
                    "No recognised state or UT names were found in the CSV."
                )
            else:
                st.session_state["uploaded_dataset"] = uploaded_df
                st.success(
                    f"Loaded {len(uploaded_df)} observation rows for "
                    "this session. This upload overrides the GitHub dataset "
                    "until the session is reset or the app is restarted."
                )
                st.dataframe(
                    uploaded_df,
                    use_container_width=True,
                    hide_index=True,
                )
        except Exception as error:
            st.error("The CSV could not be read.")
            st.code(str(error))

    current_dataset = get_dataset()
    st.subheader("Current dataset")
    st.write(
    "The current dataset below is the MPI dataset used for the map and "
    "poverty-reduction analysis. Other indicators are loaded separately "
    "from their own CSV files when selected. Some datasets are historical "
    "or contain missing values; check each indicator's source and reference year."
)
    st.write(f"Columns: {len(current_dataset.columns)}")
    st.dataframe(
        current_dataset,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download current dataset",
        data=current_dataset.to_csv(index=False).encode("utf-8"),
        file_name="india_development_atlas_data.csv",
        mime="text/csv",
    )

    st.caption(
        "To return to the default GitHub MPI data, remove the uploaded "
        "file from the uploader or restart the app session."
    )


# ============================================================
# PAGE 5: ABOUT AND SOURCES
# ============================================================

elif page == "About & Sources":
    st.header("About the India Development Atlas")
    st.write(
        """
        The India Development Atlas makes regional socioeconomic
        differences easier to explore and compare. It combines state-level
        indicators, documented data sources, and interactive visualisations.

        Missing values are not treated as zero, and development scores
        are not fabricated. Published values should include a source,
        reference period, unit, and indicator definition.
        """
    )

    st.subheader("Current dataset")
    st.write(
        "Each indicator is loaded from its dedicated CSV in this project's "
        "GitHub repository. Sources and reference periods differ by indicator, "
        "and some values are missing. In particular, the state poverty-rate "
        "series is from 2011–12 and should not be treated as current."
    )

    st.subheader("Sources")
    sources = [
        (
            "NITI Aayog: National Multidimensional Poverty Index",
            "https://www.niti.gov.in/",
        ),
        (
    "MoSPI: Periodic Labour Force Survey",
    "https://mospi.gov.in/",
),
(
    "PLFS Annual Report 2025",
    "https://www.mospi.gov.in/uploads/publications_reports/publications_reports1780040415321_0624fb13-fb47-40bc-b470-7c7e9635c3ef_PLFS_2025_F_REV_29052026.pdf",
),
        (
            "Census of India",
            "https://censusindia.gov.in/census.website/en/data",
        ),
        (
            "Rajya Sabha Q 1677 (10 Dec 2024): State/UT per-capita GSDP",
            "https://sansad.in/getFile/annex/266/AU1677_35H76u.pdf?source=pqars",
        ),
        (
            "Rajya Sabha Q 276 (4 Feb 2025): Per-capita government health expenditure",
            "https://sansad.in/getFile/annex/267/AU276_1fzsrW.pdf?source=pqars",
        ),
        (
            "Reserve Bank of India publications",
            "https://www.rbi.org.in/",
        ),
        (
            "UDISE+ school education data",
            "https://udiseplus.gov.in/",
        ),
        (
            "Open Government Data Platform India",
            "https://www.data.gov.in/",
        ),
        (
            "India Geodata repository",
            "https://github.com/yashveeeeeeer/india-geodata",
        ),
    ]

    for label, url in sources:
        st.markdown(f"- [{label}]({url})")

    st.subheader("Boundary validation")
    st.write(
        f"Matched regions: {len(matched_regions)} out of {len(REGIONS)}"
    )

    if missing_regions:
        st.warning(
            "Some expected regions were not matched: "
            + ", ".join(missing_regions)
        )
    else:
        st.success("All 28 states and 8 Union Territories were matched.")

    st.caption(
        "Boundary geometry and administrative vintage should be checked "
        "before the map is used for official or policy purposes."
    )
