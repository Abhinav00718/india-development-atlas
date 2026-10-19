

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import unicodedata

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="India Development Atlas",
    page_icon="🇮🇳",
    layout="wide",
)

st.title("🇮🇳 India Development Atlas")
st.markdown(
    """
    Explore regional development and inequality across India.
    Compare states and Union Territories using development,
    education, and healthcare indicators.
    """
)

st.caption(
    "Data status: Official indicator data has not yet been connected. "
    "N/A values are intentional."
)

# --------------------------------------------------
# REGIONS
# --------------------------------------------------

STATES = [
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
]

UNION_TERRITORIES = [
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
]

ALL_REGIONS = STATES + UNION_TERRITORIES

# --------------------------------------------------
# DATASET
# --------------------------------------------------
# These values remain None until verified official data
# is connected. Do not replace them with invented scores.

df = pd.DataFrame(
    {
        "Region": ALL_REGIONS,
        "Type": [
            "State" if region in STATES else "Union Territory"
            for region in ALL_REGIONS
        ],
        "Development Score": [None] * len(ALL_REGIONS),
        "Education Score": [None] * len(ALL_REGIONS),
        "Healthcare Score": [None] * len(ALL_REGIONS),
    }
)

INDICATORS = [
    "Development Score",
    "Education Score",
    "Healthcare Score",
]

# --------------------------------------------------
# NORMALISE REGION NAMES
# --------------------------------------------------

def normalise_name(name):
    """Standardise region names to improve GeoJSON matching."""

    if name is None:
        return ""

    name = str(name).strip()

    # Remove accents and diacritics.
    name = unicodedata.normalize("NFKD", name)
    name = "".join(
        character
        for character in name
        if not unicodedata.combining(character)
    )

    name = name.lower()
    name = name.replace("&", " and ")
    name = name.replace("_", " ")
    name = name.replace("-", " ")
    name = " ".join(name.split())

    aliases = {
        "orissa": "odisha",
        "pondicherry": "puducherry",
        "nct of delhi": "delhi",
        "national capital territory of delhi": "delhi",
        "new delhi": "delhi",
        "jammu and kashmir": "jammu and kashmir",
        "andaman and nicobar": "andaman and nicobar islands",
        "andaman nicobar islands": "andaman and nicobar islands",
        "dadra and nagar haveli": (
            "dadra and nagar haveli and daman and diu"
        ),
        "daman and diu": (
            "dadra and nagar haveli and daman and diu"
        ),
        "dadra nagar haveli and daman diu": (
            "dadra and nagar haveli and daman and diu"
        ),
    }

    return aliases.get(name, name)


df["atlas_region"] = df["Region"].apply(normalise_name)

# --------------------------------------------------
# GEOJSON SOURCE
# --------------------------------------------------

GEOJSON_URL = (
    "https://raw.githubusercontent.com/"
    "udit-001/india-maps-data/main/geojson/india.geojson"
)


@st.cache_data(ttl=86400)
def load_geojson():
    """Download GeoJSON and identify its region-name property."""

    response = requests.get(
        GEOJSON_URL,
        timeout=30,
    )
    response.raise_for_status()

    geojson = response.json()

    if geojson.get("type") != "FeatureCollection":
        raise ValueError(
            "The map file is not a GeoJSON FeatureCollection."
        )

    features = geojson.get("features", [])

    if not features:
        raise ValueError(
            "The GeoJSON file contains no map features."
        )

    # Candidate property names, in preferred order.
    possible_keys = [
        "ST_NM",
        "shapeName",
        "NAME_1",
        "st_nm",
        "state_name",
        "State_Name",
        "state",
        "State",
        "name",
        "NAME",
        "NAME_0",
        "admin",
        "region",
        "dtname",
    ]

    # Search properties across all features, not only the first.
    all_keys = set()

    for feature in features:
        all_keys.update(
            feature.get("properties", {}).keys()
        )

    name_key = next(
        (
            key
            for key in possible_keys
            if key in all_keys
        ),
        None,
    )

    if name_key is None:
        raise ValueError(
            "No recognised region-name field was found. "
            f"Available properties: {sorted(all_keys)}"
        )

    # Add a standardised field for Plotly.
    for feature in features:
        properties = feature.setdefault("properties", {})
        source_name = properties.get(name_key)

        properties["atlas_region"] = normalise_name(
            source_name
        )

    return geojson


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.header("Atlas Controls")

selected_indicator = st.sidebar.selectbox(
    "Select indicator",
    INDICATORS,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### About this atlas")
st.sidebar.write(
    "This project aims to make regional development "
    "patterns in India easier to explore and compare."
)

st.sidebar.markdown("### Planned data sources")
st.sidebar.markdown(
    "- [NITI Aayog](https://www.niti.gov.in/)"
)
st.sidebar.markdown(
    "- [RBI State Statistics](https://www.rbi.org.in/)"
)
st.sidebar.markdown(
    "- [Census of India](https://censusindia.gov.in/)"
)
st.sidebar.markdown(
    "- [UDISE+](https://www.udiseplus.gov.in/)"
)

# --------------------------------------------------
# SUMMARY METRICS
# --------------------------------------------------

col1, col2, col3 = st.columns(3)

col1.metric(
    "States",
    len(STATES),
)

col2.metric(
    "Union Territories",
    len(UNION_TERRITORIES),
)

col3.metric(
    "Regions in Atlas",
    len(ALL_REGIONS),
)

st.divider()

# --------------------------------------------------
# INDIA MAP
# --------------------------------------------------

st.subheader("Development Map")

st.write(
    f"Selected indicator: **{selected_indicator}**"
)

try:
    geojson = load_geojson()

    # Match the GeoJSON regions against our dataset.
    geojson_names = {
        feature.get("properties", {}).get("atlas_region", "")
        for feature in geojson.get("features", [])
    }

    dataset_names = set(df["atlas_region"])

    matched_regions = geojson_names.intersection(dataset_names)

    if not matched_regions:
        st.warning(
            "The map loaded, but none of its region names matched "
            "the atlas dataset. The GeoJSON may use different "
            "state names or may contain district boundaries instead."
        )

        st.caption(
            "GeoJSON region-name examples: "
            + ", ".join(sorted(name for name in geojson_names if name)[:15])
        )

    map_df = df[
        df["atlas_region"].isin(geojson_names)
    ].copy()

    if map_df.empty:
        st.warning(
            "No atlas regions matched the map boundaries."
        )
    elif map_df[selected_indicator].notna().sum() == 0:
        st.info(
            "The map boundaries loaded, but the selected indicator "
            "does not have data yet. Add verified official values "
            "to colour the map."
        )

        fig = px.choropleth(
            map_df,
            geojson=geojson,
            locations="atlas_region",
            featureidkey="properties.atlas_region",
            color=None,
            hover_name="Region",
            hover_data={
                "Type": True,
                "atlas_region": False,
            },
            title="India: Regional Boundaries",
        )

        fig.update_geos(
            fitbounds="locations",
            visible=False,
        )

        fig.update_layout(
            height=650,
            margin={
                "r": 0,
                "t": 50,
                "l": 0,
                "b": 0,
            },
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    else:
        fig = px.choropleth(
            map_df.dropna(subset=[selected_indicator]),
            geojson=geojson,
            locations="atlas_region",
            featureidkey="properties.atlas_region",
            color=selected_indicator,
            hover_name="Region",
            hover_data={
                "Type": True,
                selected_indicator: True,
                "atlas_region": False,
            },
            color_continuous_scale="YlGnBu",
            title=f"India: {selected_indicator}",
        )

        fig.update_geos(
            fitbounds="locations",
            visible=False,
        )

        fig.update_layout(
            height=650,
            margin={
                "r": 0,
                "t": 50,
                "l": 0,
                "b": 0,
            },
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    unmatched_regions = sorted(
        dataset_names - geojson_names
    )

    if unmatched_regions:
        with st.expander("Regions not matched to map boundaries"):
            st.write(
                [
                    region
                    for region in ALL_REGIONS
                    if normalise_name(region) in unmatched_regions
                ]
            )

except Exception as error:
    st.error(
        "The map could not be loaded. "
        "Check the GeoJSON source and its structure."
    )

    with st.expander("Technical details"):
        st.code(str(error))

    st.info(
        "The region explorer, comparison tool, and dataset table "
        "can still be used while the map source is being fixed."
    )

# --------------------------------------------------
# REGION EXPLORER
# --------------------------------------------------

st.divider()
st.subheader("Explore a Region")

selected_region = st.selectbox(
    "Choose a state or Union Territory",
    ALL_REGIONS,
)

region_data = df[
    df["Region"] == selected_region
].iloc[0]

st.markdown(f"### {selected_region}")

metric1, metric2, metric3 = st.columns(3)

for column, indicator in zip(
    [metric1, metric2, metric3],
    INDICATORS,
):
    value = region_data[indicator]

    display_value = (
        "N/A"
        if pd.isna(value)
        else f"{value:.1f}"
    )

    column.metric(
        indicator,
        display_value,
    )

st.caption(
    "N/A means a verified value has not been added yet. "
    "It does not mean the region scored zero."
)

# --------------------------------------------------
# REGION COMPARISON
# --------------------------------------------------

st.divider()
st.subheader("Compare Regions")

comparison_regions = st.multiselect(
    "Select regions to compare",
    ALL_REGIONS,
    default=["Tamil Nadu", "Kerala", "Karnataka"],
)

if comparison_regions:
    comparison_df = df[
        df["Region"].isin(comparison_regions)
    ].copy()

    comparison_long = comparison_df.melt(
        id_vars=["Region", "Type"],
        value_vars=INDICATORS,
        var_name="Indicator",
        value_name="Score",
    )

    available_comparison = comparison_long.dropna(
        subset=["Score"]
    )

    if available_comparison.empty:
        st.info(
            "No official scores are available for the selected "
            "regions yet. Once data is added, this section will "
            "display a visual comparison."
        )
    else:
        comparison_fig = px.bar(
            available_comparison,
            x="Region",
            y="Score",
            color="Indicator",
            barmode="group",
            title="Indicator Comparison",
            hover_data=["Type"],
        )

        comparison_fig.update_layout(
            yaxis_title="Score",
            xaxis_title="Region",
        )

        st.plotly_chart(
            comparison_fig,
            use_container_width=True,
        )

    st.dataframe(
        comparison_df[
            ["Region", "Type"] + INDICATORS
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info(
        "Select at least one region to compare."
    )

# --------------------------------------------------
# COMPLETE DATASET
# --------------------------------------------------

st.divider()
st.subheader("All Regions")

st.dataframe(
    df[
        ["Region", "Type"] + INDICATORS
    ],
    use_container_width=True,
    hide_index=True,
)

csv_data = df[
    ["Region", "Type"] + INDICATORS
].to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download dataset as CSV",
    data=csv_data,
    file_name="india_development_atlas.csv",
    mime="text/csv",
)

# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "India Development Atlas | Educational and research project. "
    "Indicator values will be added after verification against "
    "official sources."
)
