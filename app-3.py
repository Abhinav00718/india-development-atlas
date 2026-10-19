
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
    "Official indicator data has not yet been connected. "
    "N/A values are intentional."
)

# --------------------------------------------------
# STATES AND UNION TERRITORIES
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

INDICATORS = [
    "Development Score",
    "Education Score",
    "Healthcare Score",
]

# --------------------------------------------------
# DATASET
# --------------------------------------------------

df = pd.DataFrame({
    "Region": ALL_REGIONS,
    "Type": [
        "State" if region in STATES else "Union Territory"
        for region in ALL_REGIONS
    ],
    "Development Score": [None] * len(ALL_REGIONS),
    "Education Score": [None] * len(ALL_REGIONS),
    "Healthcare Score": [None] * len(ALL_REGIONS),
})

# --------------------------------------------------
# NORMALISE REGION NAMES
# --------------------------------------------------

def normalise_name(name):
    """Standardise names to improve map-to-data matching."""

    if name is None:
        return ""

    name = str(name).strip()

    name = unicodedata.normalize("NFKD", name)
    name = "".join(
        char for char in name
        if not unicodedata.combining(char)
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
# This simplified source is intended for web mapping.
# Its documented coverage is 32 regions, not all 36 UT/state units.

GEOJSON_URL = (
    "https://raw.githubusercontent.com/"
    "AbhinavSwami28/india-official-geojson/"
    "main/india-states-simplified.geojson"
)


@st.cache_data(ttl=86400)
def load_geojson():
    """Download GeoJSON and standardise region names."""

    response = requests.get(GEOJSON_URL, timeout=45)
    response.raise_for_status()

    geojson = response.json()

    if geojson.get("type") != "FeatureCollection":
        raise ValueError(
            "The map source is not a GeoJSON FeatureCollection."
        )

    features = geojson.get("features", [])

    if not features:
        raise ValueError(
            "The GeoJSON file contains no features."
        )

    # Search across every feature for available property names.
    all_keys = set()

    for feature in features:
        all_keys.update(
            feature.get("properties", {}).keys()
        )

    possible_keys = [
        "shapeName",
        "ST_NM",
        "state_name",
        "State_Name",
        "st_nm",
        "NAME_1",
        "state",
        "State",
        "name",
        "NAME",
        "admin",
        "region",
    ]

    name_key = next(
        (key for key in possible_keys if key in all_keys),
        None,
    )

    if name_key is None:
        raise ValueError(
            "Could not identify the region-name property. "
            f"Available properties: {sorted(all_keys)}"
        )

    for feature in features:
        properties = feature.setdefault("properties", {})
        source_name = properties.get(name_key)

        properties["atlas_region"] = normalise_name(source_name)

    return geojson, name_key


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.header("Atlas Controls")

selected_indicator = st.sidebar.selectbox(
    "Select indicator",
    INDICATORS,
)

st.sidebar.divider()

st.sidebar.markdown("### About this atlas")
st.sidebar.write(
    "An interactive project for exploring regional "
    "development and inequality across India."
)

st.sidebar.markdown("### Planned data sources")

st.sidebar.markdown(
    "- [NITI Aayog](https://www.niti.gov.in/)\n"
    "- [RBI State Statistics](https://www.rbi.org.in/)\n"
    "- [Census of India](https://censusindia.gov.in/)\n"
    "- [UDISE+](https://www.udiseplus.gov.in/)"
)

# --------------------------------------------------
# SUMMARY METRICS
# --------------------------------------------------

col1, col2, col3 = st.columns(3)

col1.metric("States", len(STATES))
col2.metric("Union Territories", len(UNION_TERRITORIES))
col3.metric("Regions in Atlas", len(ALL_REGIONS))

st.divider()

# --------------------------------------------------
# INDIA MAP
# --------------------------------------------------

st.subheader("Development Map")
st.write(f"Selected indicator: **{selected_indicator}**")

try:
    geojson, detected_name_key = load_geojson()

    geojson_names = {
        feature.get("properties", {}).get("atlas_region", "")
        for feature in geojson.get("features", [])
    }

    dataset_names = set(df["atlas_region"])
    matched_regions = geojson_names.intersection(dataset_names)

    map_df = df[
        df["atlas_region"].isin(geojson_names)
    ].copy()

    if not matched_regions:
        st.warning(
            "The GeoJSON loaded, but its region names did not match "
            "the atlas dataset."
        )
        st.caption(
            "Example GeoJSON names: "
            + ", ".join(
                sorted(name for name in geojson_names if name)[:15]
            )
        )

    elif map_df[selected_indicator].notna().sum() == 0:
        # Show boundaries even before indicator data is available.
        fig = px.choropleth(
            map_df,
            geojson=geojson,
            locations="atlas_region",
            featureidkey="properties.atlas_region",
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
            height=680,
            margin=dict(l=0, r=0, t=50, b=0),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

        st.info(
            "The boundaries are displayed without indicator shading "
            "because verified scores have not been added yet."
        )

    else:
        available_df = map_df.dropna(
            subset=[selected_indicator]
        )

        fig = px.choropleth(
            available_df,
            geojson=geojson,
            locations="atlas_region",
            featureidkey="properties.atlas_region",
            color=selected_indicator,
            color_continuous_scale="YlGnBu",
            hover_name="Region",
            hover_data={
                "Type": True,
                selected_indicator: True,
                "atlas_region": False,
            },
            title=f"India: {selected_indicator}",
        )

        fig.update_geos(
            fitbounds="locations",
            visible=False,
        )

        fig.update_layout(
            height=680,
            margin=dict(l=0, r=0, t=50, b=0),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    unmatched_regions = sorted(dataset_names - geojson_names)

    if unmatched_regions:
        with st.expander("Regions not included in this map source"):
            st.write([
                region
                for region in ALL_REGIONS
                if normalise_name(region) in unmatched_regions
            ])

    st.caption(
        f"Map source property detected: {detected_name_key}. "
        f"Matched {len(matched_regions)} of {len(ALL_REGIONS)} "
        "atlas regions."
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
        "remain available even if the map fails."
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

region_data = df[df["Region"] == selected_region].iloc[0]

st.markdown(f"### {selected_region}")

metric1, metric2, metric3 = st.columns(3)

for column, indicator in zip(
    [metric1, metric2, metric3],
    INDICATORS,
):
    value = region_data[indicator]

    display_value = (
        "N/A" if pd.isna(value) else f"{value:.1f}"
    )

    column.metric(indicator, display_value)

st.caption(
    "N/A means verified data has not been added. "
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
            "No verified scores are available for these regions yet. "
            "The chart will appear once indicator values are added."
        )
    else:
        comparison_fig = px.bar(
            available_comparison,
            x="Region",
            y="Score",
            color="Indicator",
            barmode="group",
            title="Regional Indicator Comparison",
            hover_data=["Type"],
        )

        comparison_fig.update_layout(
            xaxis_title="Region",
            yaxis_title="Score",
        )

        st.plotly_chart(
            comparison_fig,
            use_container_width=True,
        )

    st.dataframe(
        comparison_df[["Region", "Type"] + INDICATORS],
        use_container_width=True,
        hide_index=True,
    )

else:
    st.info("Select at least one region to compare.")

# --------------------------------------------------
# COMPLETE DATASET
# --------------------------------------------------

st.divider()
st.subheader("All Regions")

st.dataframe(
    df[["Region", "Type"] + INDICATORS],
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
