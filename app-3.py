

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import unicodedata

st.set_page_config(
    page_title="India Development Atlas",
    page_icon="🇮🇳",
    layout="wide"
)

# ==================================================
# 1. ALL 28 STATES AND 8 UNION TERRITORIES
# ==================================================

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

ALL_REGIONS = sorted(STATES + UNION_TERRITORIES)

INDICATORS = [
    "Development Score",
    "Education Score",
    "Healthcare Score",
]

# ==================================================
# 2. DATA
# Scores are blank until sourced data is added.
# ==================================================

df = pd.DataFrame({
    "State": ALL_REGIONS,
    "Development Score": [None] * len(ALL_REGIONS),
    "Education Score": [None] * len(ALL_REGIONS),
    "Healthcare Score": [None] * len(ALL_REGIONS),
})

# ==================================================
# 3. PAGE HEADER
# ==================================================

st.title("🇮🇳 India Development Atlas")

st.markdown(
    "Explore regional development, public services, "
    "and socioeconomic disparities across India."
)

st.warning(
    "Official data has not yet been connected. Scores are currently "
    "unavailable, not zero. No state or union territory is ranked "
    "until verified data is added."
)

# ==================================================
# 4. SIDEBAR
# ==================================================

st.sidebar.title("Explore India")

indicator = st.sidebar.selectbox(
    "Choose an indicator",
    INDICATORS,
)

region_type = st.sidebar.selectbox(
    "Region type",
    ["All regions", "States only", "Union territories only"],
)

if region_type == "States only":
    visible_regions = sorted(STATES)
elif region_type == "Union territories only":
    visible_regions = sorted(UNION_TERRITORIES)
else:
    visible_regions = ALL_REGIONS

filtered_df = df[df["State"].isin(visible_regions)].copy()

st.sidebar.caption(
    "India has 28 states and 8 union territories. "
    "Indicator values will be added from verified sources."
)

# ==================================================
# 5. SUMMARY METRICS
# ==================================================

m1, m2, m3 = st.columns(3)

m1.metric("States", len(STATES))
m2.metric("Union territories", len(UNION_TERRITORIES))
m3.metric("Total regions", len(ALL_REGIONS))

st.divider()

# ==================================================
# 6. MAP BOUNDARIES
# ==================================================

# Community-maintained GeoJSON. The file is fetched at runtime.
# Boundary coverage and names should be verified before publication.
GEOJSON_URL = (
    "https://raw.githubusercontent.com/"
    "udit-001/india-maps-data/main/geojson/india.geojson"
)


def normalise_name(value):
    """Normalise geographic names for matching."""
    if value is None:
        return ""

    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )

    value = value.lower().strip()
    value = value.replace("&", "and")
    value = " ".join(value.split())

    aliases = {
        "orissa": "odisha",
        "pondicherry": "puducherry",
        "nct of delhi": "delhi",
        "national capital territory of delhi": "delhi",
        "jammu & kashmir": "jammu and kashmir",
        "andaman and nicobar": "andaman and nicobar islands",
        "dadra and nagar haveli": (
            "dadra and nagar haveli and daman and diu"
        ),
        "daman and diu": (
            "dadra and nagar haveli and daman and diu"
        ),
    }

    return aliases.get(value, value)


@st.cache_data(ttl=86400)
def load_geojson():
    response = requests.get(GEOJSON_URL, timeout=30)
    response.raise_for_status()

    geojson = response.json()

    if geojson.get("type") != "FeatureCollection":
        raise ValueError("The map file is not a GeoJSON FeatureCollection.")

    features = geojson.get("features", [])

    if not features:
        raise ValueError("The GeoJSON file contains no map features.")

    # Identify the property containing region names.
    possible_keys = [
        "ST_NM",
        "shapeName",
        "NAME_1",
        "name",
        "NAME",
        "state",
        "State",
    ]

    name_key = None

    for key in possible_keys:
        if any(
            key in feature.get("properties", {})
            for feature in features
        ):
            name_key = key
            break

    if name_key is None:
        raise ValueError(
            "Could not identify state names in the GeoJSON properties."
        )

    # Create a standard property for Plotly matching.
    for feature in features:
        properties = feature.setdefault("properties", {})
        source_name = properties.get(name_key)

        properties["atlas_region"] = normalise_name(source_name)

    return geojson


# ==================================================
# 7. INTERACTIVE MAP
# ==================================================

st.header("Interactive map of India")
st.caption(
    f"Selected indicator: {indicator}. "
    "Hover over a mapped region to inspect its available value."
)

try:
    geojson = load_geojson()

    # Match map features to the regions listed above.
    region_lookup = {
        normalise_name(region): region
        for region in ALL_REGIONS
    }

    map_records = []

    for feature in geojson["features"]:
        properties = feature.get("properties", {})
        map_name = properties.get("atlas_region", "")
        matched_region = region_lookup.get(map_name)

        if matched_region is None:
            continue

        score = df.loc[
            df["State"] == matched_region, indicator
        ].iloc[0]

        map_records.append({
            "State": matched_region,
            "Score": score,
            "Status": (
                "Data unavailable"
                if pd.isna(score)
                else "Data available"
            ),
        })

    map_df = pd.DataFrame(map_records)

    if map_df.empty:
        st.error(
            "The GeoJSON loaded, but its region names did not match "
            "the atlas. The map source's naming convention needs "
            "to be checked."
        )
    else:
        # A neutral map is shown while scores are unavailable.
        # Once official numeric values are loaded, regions will be coloured.
        if map_df["Score"].notna().any():
            fig_map = px.choropleth(
                map_df,
                geojson=geojson,
                locations="State",
                featureidkey="properties.atlas_region",
                color="Score",
                hover_name="State",
                hover_data={
                    "Score": True,
                    "Status": True,
                },
                color_continuous_scale="Teal",
                range_color=(0, 100),
                labels={"Score": indicator},
            )
        else:
            map_df["Map status"] = "Official data not yet added"

            fig_map = px.choropleth(
                map_df,
                geojson=geojson,
                locations="State",
                featureidkey="properties.atlas_region",
                color="Map status",
                hover_name="State",
                hover_data={
                    "Map status": True,
                },
                color_discrete_map={
                    "Official data not yet added": "#C8D5D8"
                },
            )

        fig_map.update_geos(
            fitbounds="locations",
            visible=False,
        )

        fig_map.update_layout(
            height=680,
            margin=dict(l=0, r=0, t=30, b=0),
            template="plotly_white",
            legend_title_text="Data status",
        )

        st.plotly_chart(
            fig_map,
            use_container_width=True,
        )

        matched_names = set(map_df["State"])
        missing_names = sorted(set(ALL_REGIONS) - matched_names)

        st.caption(
            f"Matched {len(matched_names)} of {len(ALL_REGIONS)} "
            "regions to the map boundary file."
        )

        if missing_names:
            with st.expander(
                "Regions missing from the map boundary file"
            ):
                st.write(
                    "These names need to be reconciled with the "
                    "boundary source:"
                )
                st.write(", ".join(missing_names))

except Exception as error:
    st.error(
        "The map could not be loaded. Check your internet connection "
        "and the GeoJSON source."
    )
    st.caption(f"Technical detail: {error}")

# ==================================================
# 8. REGION EXPLORER
# ==================================================

st.divider()
st.header("Explore an individual region")

selected_region = st.selectbox(
    "Choose a state or union territory",
    visible_regions,
)

selected_row = df.loc[
    df["State"] == selected_region
].iloc[0]

if selected_region in STATES:
    st.caption("Region type: State")
else:
    st.caption("Region type: Union territory")

st.subheader(selected_region)

c1, c2, c3 = st.columns(3)

for column, metric_name in zip(
    [c1, c2, c3],
    INDICATORS,
):
    value = selected_row[metric_name]

    if pd.isna(value):
        display_value = "N/A"
    else:
        display_value = f"{value:.1f}/100"

    column.metric(metric_name, display_value)

st.info(
    "This region's scores will appear once verified official data "
    "has been connected. N/A means unavailable, not zero."
)

# ==================================================
# 9. COMPARE TWO REGIONS
# ==================================================

st.divider()
st.header("Compare two regions")

compare_col1, compare_col2 = st.columns(2)

with compare_col1:
    region_a = st.selectbox(
        "First region",
        visible_regions,
        index=0,
        key="region_a",
    )

with compare_col2:
    default_b = min(1, len(visible_regions) - 1)

    region_b = st.selectbox(
        "Second region",
        visible_regions,
        index=default_b,
        key="region_b",
    )

score_a = df.loc[
    df["State"] == region_a, indicator
].iloc[0]

score_b = df.loc[
    df["State"] == region_b, indicator
].iloc[0]

compare1, compare2, compare3 = st.columns(3)

compare1.metric(
    region_a,
    "N/A" if pd.isna(score_a) else f"{score_a:.1f}/100",
)

compare2.metric(
    region_b,
    "N/A" if pd.isna(score_b) else f"{score_b:.1f}/100",
)

if pd.isna(score_a) or pd.isna(score_b):
    difference = "N/A"
else:
    difference = f"{abs(score_a - score_b):.1f} points"

compare3.metric("Absolute difference", difference)

# ==================================================
# 10. DATA TABLE AND DOWNLOAD
# ==================================================

st.divider()
st.header("Explore the regional dataset")

st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "Download regional dataset (CSV)",
    data=filtered_df.to_csv(index=False).encode("utf-8"),
    file_name="india_development_atlas.csv",
    mime="text/csv",
)

# ==================================================
# 11. SOURCES AND METHODOLOGY
# ==================================================

st.divider()
st.header("Data sources and methodology")

st.markdown(
    """
    The atlas is currently a prototype. It does not yet contain
    verified development, education, or healthcare scores.

    Planned official data sources:

    - [NITI Aayog](https://www.niti.gov.in/)
    - [Census of India](https://censusindia.gov.in/)
    - [Reserve Bank of India: State statistics](https://www.rbi.org.in/)
    - [UDISE+ education statistics](https://www.udiseplus.gov.in/)
    - [Open Government Data Platform](https://www.data.gov.in/)

    Map boundaries are loaded from a community-maintained GeoJSON
    source and should be independently checked before publication.

    Each official indicator should eventually include its source,
    reference year, definition, unit, and known limitations.
    """
)

st.caption(
    "India Development Atlas | Prototype | Missing values are "
    "not interpreted as zero."
)
