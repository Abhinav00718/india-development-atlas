
import json
import re

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="India Development Atlas",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------

GEOJSON_URL = (
    "https://raw.githubusercontent.com/"
    "india-in-data/india_maps/master/"
    "india_state_ut_administered.geojson"
)

REQUEST_TIMEOUT = 30

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

REGION_ALIASES = {
    "nct of delhi": "Delhi",
    "national capital territory of delhi": "Delhi",
    "orissa": "Odisha",
    "uttaranchal": "Uttarakhand",
    "jammu & kashmir": "Jammu and Kashmir",
    "andaman & nicobar islands": "Andaman and Nicobar Islands",
    "andaman and nicobar": "Andaman and Nicobar Islands",
    "pondicherry": "Puducherry",
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
    "nct": "Delhi",
}

# These are placeholders until actual official indicator data
# are connected. Do not interpret them as real development scores.
INDICATORS = {
    "Overall development score": {
        "column": "Development_Score",
        "unit": "Index",
        "description": "Composite development score",
    },
    "Multidimensional poverty": {
        "column": "MPI_Poverty",
        "unit": "%",
        "description": "Population experiencing multidimensional poverty",
    },
    "Literacy rate": {
        "column": "Literacy_Rate",
        "unit": "%",
        "description": "Literacy rate",
    },
    "Per-capita income": {
        "column": "Per_Capita_Income",
        "unit": "₹",
        "description": "Per-capita income",
    },
    "Unemployment rate": {
        "column": "Unemployment_Rate",
        "unit": "%",
        "description": "Unemployment rate",
    },
}


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def normalise_name(value):
    """Standardise region names for matching GeoJSON and data."""

    if value is None:
        return ""

    name = str(value).strip().lower()
    name = name.replace("&", "and")
    name = re.sub(r"[_-]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    if name in REGION_ALIASES:
        return REGION_ALIASES[name]

    for region in REGIONS:
        if name == region.lower():
            return region

    return name.title()


def find_region_property(features):
    """Find the GeoJSON property containing state/UT names."""

    preferred_keys = [
        "STNAME",
        "stname",
        "NAME_1",
        "name_1",
        "state_name",
        "State_Name",
        "STATE",
        "State",
        "state",
        "ST_NM",
        "st_nm",
        "shapeName",
        "NAME",
        "name",
        "NAME_0",
        "admin",
        "region",
    ]

    if not features:
        raise ValueError("The GeoJSON contains no features.")

    existing_keys = set()

    for feature in features:
        properties = feature.get("properties", {})
        existing_keys.update(properties.keys())

    # Try recognised property names first.
    for key in preferred_keys:
        if key not in existing_keys:
            continue

        values = [
            feature.get("properties", {}).get(key)
            for feature in features
        ]

        matched = sum(
            normalise_name(value) in REGIONS
            for value in values
        )

        if matched >= 20:
            return key

    # Fallback: inspect all properties and select the one that
    # matches the largest number of known state/UT names.
    best_key = None
    best_count = 0

    for key in existing_keys:
        values = [
            feature.get("properties", {}).get(key)
            for feature in features
        ]

        matched = sum(
            normalise_name(value) in REGIONS
            for value in values
        )

        if matched > best_count:
            best_key = key
            best_count = matched

    if best_key is None or best_count < 20:
        raise ValueError(
            "Could not identify state/UT names in the GeoJSON. "
            f"Best property: {best_key!r}; matches: {best_count}."
        )

    return best_key


@st.cache_data(ttl=86400, show_spinner=False)
def load_geojson():
    """Download and prepare India's state/UT GeoJSON."""

    response = requests.get(
        GEOJSON_URL,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": "IndiaDevelopmentAtlas/1.0"},
    )
    response.raise_for_status()

    geojson = response.json()

    if geojson.get("type") != "FeatureCollection":
        raise ValueError(
            "The map source did not return a GeoJSON FeatureCollection."
        )

    features = geojson.get("features", [])

    if not features:
        raise ValueError("The GeoJSON FeatureCollection is empty.")

    name_key = find_region_property(features)

    prepared_features = []
    matched_regions = set()
    skipped_features = 0

    for feature in features:
        properties = feature.get("properties", {})
        raw_name = properties.get(name_key)
        region_name = normalise_name(raw_name)

        geometry = feature.get("geometry")

        if not geometry or not geometry.get("coordinates"):
            skipped_features += 1
            continue

        # Avoid plotting unrelated features that cannot be matched
        # to a recognised Indian state or union territory.
        if region_name not in REGIONS:
            skipped_features += 1
            continue

        # Work on a copy rather than mutating the downloaded object.
        prepared = {
            "type": "Feature",
            "properties": {
                **properties,
                "atlas_region": region_name,
            },
            "geometry": geometry,
        }

        prepared_features.append(prepared)
        matched_regions.add(region_name)

    if not prepared_features:
        raise ValueError(
            "The GeoJSON loaded, but no state/UT features matched. "
            f"Detected name property: {name_key!r}."
        )

    prepared_geojson = {
        "type": "FeatureCollection",
        "features": prepared_features,
    }

    missing_regions = sorted(set(REGIONS) - matched_regions)

    return (
        prepared_geojson,
        sorted(matched_regions),
        missing_regions,
        name_key,
        skipped_features,
    )


@st.cache_data(show_spinner=False)
def create_empty_dataset():
    """Create a blank data template without inventing scores."""

    data = pd.DataFrame({"Region": REGIONS})

    data["Development_Score"] = None
    data["MPI_Poverty"] = None
    data["Literacy_Rate"] = None
    data["Per_Capita_Income"] = None
    data["Unemployment_Rate"] = None
    data["Data_Year"] = None
    data["Data_Source"] = None

    return data


def format_value(value, indicator):
    """Format a displayed indicator value."""

    if pd.isna(value):
        return "Not available"

    unit = INDICATORS[indicator]["unit"]

    if unit == "₹":
        return f"₹{value:,.0f}"

    if unit == "%":
        return f"{value:.1f}%"

    return f"{value:.2f}"


def make_map(geojson, dataset, indicator):
    """Build a state-level choropleth with a stable India view."""

    column = INDICATORS[indicator]["column"]

    value_lookup = dataset.set_index("Region")[column].to_dict()

    locations = []
    values = []
    customdata = []

    for feature in geojson["features"]:
        region = feature["properties"]["atlas_region"]
        value = value_lookup.get(region)

        locations.append(region)

        # Plotly needs numeric values to render polygons. Zero here
        # is only a neutral placeholder when data are missing, not
        # a claim that the region's real indicator value is zero.
        values.append(
            float(value) if pd.notna(value) else 0.0
        )

        customdata.append([
            region,
            format_value(value, indicator),
            (
                str(dataset.loc[
                    dataset["Region"] == region, "Data_Year"
                ].iloc[0])
                if not dataset.loc[
                    dataset["Region"] == region, "Data_Year"
                ].empty
                and pd.notna(dataset.loc[
                    dataset["Region"] == region, "Data_Year"
                ].iloc[0])
                else "Not available"
            ),
        ])

    has_data = dataset[column].notna().any()

    if has_data:
        colorscale = [
            [0.0, "#E0F2FE"],
            [0.5, "#60A5FA"],
            [1.0, "#1D4ED8"],
        ]
        zmin = float(dataset[column].min())
        zmax = float(dataset[column].max())

        if zmin == zmax:
            zmax = zmin + 1
    else:
        # A single neutral fill until genuine data are loaded.
        colorscale = [
            [0.0, "#DCE6F1"],
            [1.0, "#DCE6F1"],
        ]
        zmin = 0
        zmax = 1

    fig = go.Figure(
        go.Choropleth(
            geojson=geojson,
            featureidkey="properties.atlas_region",
            locations=locations,
            z=values,
            customdata=customdata,
            colorscale=colorscale,
            zmin=zmin,
            zmax=zmax,
            marker={
                "line": {
                    "color": "#FFFFFF",
                    "width": 0.8,
                }
            },
            colorbar=(
                {
                    "title": INDICATORS[indicator]["unit"],
                    "thickness": 14,
                    "len": 0.65,
                }
                if has_data
                else None
            ),
            showscale=False,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                + indicator
                + ": %{customdata[1]}<br>"
                + "Data year: %{customdata[2]}"
                + "<extra></extra>"
            ),
        )
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        showland=True,
        landcolor="#F8FAFC",
        showocean=False,
        showcoastlines=False,
        showcountries=False,
        bgcolor="white",
        projection_type="mercator",
    )

    fig.update_layout(
        height=650,
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
        paper_bgcolor="white",
        plot_bgcolor="white",
        geo={
            "bgcolor": "white",
        },
        font={"color": "#1F2937"},
    )

    return fig, has_data


# ---------------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------------

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
        max-width: 1500px;
    }

    h1, h2, h3 {
        letter-spacing: -0.025em;
    }

    .atlas-subtitle {
        color: #64748b;
        font-size: 1.05rem;
        margin-top: -0.5rem;
        margin-bottom: 1.5rem;
    }

    .atlas-note {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px 16px;
        color: #334155;
        margin: 10px 0 16px 0;
    }

    footer {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

st.sidebar.title("🇮🇳 India Development Atlas")

st.sidebar.caption(
    "Explore regional development, disparities and indicators."
)

st.sidebar.divider()

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

st.sidebar.markdown("### Data status")
st.sidebar.info(
    "The current version uses a geographic boundary file. "
    "Development indicator values have not yet been connected "
    "to official datasets."
)

st.sidebar.markdown(
    "[NITI Aayog](https://www.niti.gov.in/)  \n"
    "[Census of India](https://censusindia.gov.in/)  \n"
    "[Reserve Bank of India](https://www.rbi.org.in/)  \n"
    "[UDISE+](https://www.udiseplus.gov.in/)  \n"
    "[data.gov.in](https://www.data.gov.in/)"
)


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

dataset = create_empty_dataset()

try:
    (
        geojson,
        matched_regions,
        missing_regions,
        detected_name_key,
        skipped_features,
    ) = load_geojson()

    map_error = None

except Exception as exc:
    geojson = None
    matched_regions = []
    missing_regions = REGIONS.copy()
    detected_name_key = None
    skipped_features = 0
    map_error = str(exc)


# ---------------------------------------------------------
# PAGE 1: DEVELOPMENT MAP
# ---------------------------------------------------------

if page == "Development Map":

    st.title("India: Development Atlas")

    st.markdown(
        '<div class="atlas-subtitle">'
        "An interactive view of regional development across "
        "India's states and union territories."
        "</div>",
        unsafe_allow_html=True,
    )

    selected_indicator = st.selectbox(
        "Select an indicator",
        list(INDICATORS.keys()),
    )

    left, middle, right = st.columns(3)

    left.metric("States and UTs in atlas", len(REGIONS))
    middle.metric("Regions matched in map", len(matched_regions))
    right.metric("Indicators selected", len(INDICATORS))

    if map_error:
        st.error(
            "The map data could not be loaded. "
            "The app has not silently substituted a fake map."
        )

        with st.expander("Technical details"):
            st.code(map_error)

        st.markdown(
            f"[Open the GeoJSON source]({GEOJSON_URL})"
        )

    else:
        fig, has_data = make_map(
            geojson,
            dataset,
            selected_indicator,
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displaylogo": False,
                "scrollZoom": False,
                "responsive": True,
            },
        )

        if not has_data:
            st.info(
                "The geographic boundaries are displayed, but "
                "indicator values are not connected yet. The "
                "neutral fill is not a development ranking."
            )

        if missing_regions:
            with st.expander(
                f"Regions missing from the boundary file ({len(missing_regions)})"
            ):
                st.write(", ".join(missing_regions))
                st.caption(
                    "These regions cannot be shown until the "
                    "boundary source or its name matching is corrected."
                )

    st.subheader("About this map")

    st.write(
        "This atlas is designed to compare development outcomes "
        "across Indian regions. The map currently provides the "
        "geographic framework. Official indicator data must be "
        "added and documented before meaningful comparisons can "
        "be made."
    )


# ---------------------------------------------------------
# PAGE 2: EXPLORE A REGION
# ---------------------------------------------------------

elif page == "Explore a Region":

    st.title("Explore a Region")

    selected_region = st.selectbox(
        "Choose a state or union territory",
        REGIONS,
    )

    region_row = dataset.loc[
        dataset["Region"] == selected_region
    ].iloc[0]

    st.subheader(selected_region)

    if geojson and selected_region not in matched_regions:
        st.warning(
            "This region is in the atlas list but was not matched "
            "to the current geographic boundary file."
        )

    st.markdown("### Development indicators")

    cols = st.columns(3)

    display_indicators = [
        "Overall development score",
        "Multidimensional poverty",
        "Literacy rate",
        "Per-capita income",
        "Unemployment rate",
    ]

    for index, indicator in enumerate(display_indicators):
        column = INDICATORS[indicator]["column"]
        value = region_row[column]

        cols[index % 3].metric(
            indicator,
            format_value(value, indicator),
        )

    st.markdown("### Available information")

    st.write(
        "Once official datasets are connected, this page will "
        "show the selected region's indicator values, source, "
        "year, and comparisons with national figures."
    )

    st.dataframe(
        pd.DataFrame({
            "Indicator": display_indicators,
            "Value": [
                format_value(
                    region_row[INDICATORS[indicator]["column"]],
                    indicator,
                )
                for indicator in display_indicators
            ],
        }),
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------
# PAGE 3: COMPARE REGIONS
# ---------------------------------------------------------

elif page == "Compare Regions":

    st.title("Compare Regions")

    st.write(
        "Select regions to compare their development indicators."
    )

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

    column = INDICATORS[selected_indicator]["column"]

    comparison = dataset[
        dataset["Region"].isin(selected_regions)
    ][["Region", column, "Data_Year", "Data_Source"]].copy()

    comparison = comparison.rename(
        columns={
            column: selected_indicator,
            "Data_Year": "Data year",
            "Data_Source": "Data source",
        }
    )

    if comparison.empty:
        st.info("Select at least one region to display a comparison.")

    else:
        st.dataframe(
            comparison,
            use_container_width=True,
            hide_index=True,
        )

        if comparison[selected_indicator].notna().any():
            ranked = comparison.dropna(
                subset=[selected_indicator]
            ).sort_values(
                selected_indicator,
                ascending=False,
            )

            st.subheader("Comparison chart")

            chart = go.Figure(
                go.Bar(
                    x=ranked["Region"],
                    y=ranked[selected_indicator],
                    text=ranked[selected_indicator],
                    textposition="auto",
                )
            )

            chart.update_layout(
                xaxis_title="Region",
                yaxis_title=INDICATORS[selected_indicator]["unit"],
                height=420,
                margin={"l": 10, "r": 10, "t": 20, "b": 10},
            )

            st.plotly_chart(
                chart,
                use_container_width=True,
            )

        else:
            st.info(
                "No indicator values are available to plot yet. "
                "Connect an official dataset to enable rankings "
                "and comparison charts."
            )


# ---------------------------------------------------------
# PAGE 4: DATA EXPLORER
# ---------------------------------------------------------

elif page == "Data Explorer":

    st.title("Data Explorer")

    st.write(
        "View the region-level dataset and download a CSV template."
    )

    st.caption(
        "The current indicator columns are intentionally blank. "
        "They are placeholders, not official statistics."
    )

    search_text = st.text_input(
        "Search for a region",
        placeholder="For example, Karnataka",
    )

    filtered_data = dataset.copy()

    if search_text.strip():
        filtered_data = filtered_data[
            filtered_data["Region"].str.contains(
                search_text.strip(),
                case=False,
                na=False,
            )
        ]

    st.dataframe(
        filtered_data,
        use_container_width=True,
        hide_index=True,
    )

    csv_data = dataset.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download dataset template (CSV)",
        data=csv_data,
        file_name="india_development_atlas_template.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------
# PAGE 5: ABOUT & SOURCES
# ---------------------------------------------------------

elif page == "About & Sources":

    st.title("About the India Development Atlas")

    st.write(
        """
        The India Development Atlas is an interactive project for
        exploring regional differences in socioeconomic development
        across India's states and union territories.

        Its aim is to bring together comparable indicators on
        poverty, education, income, employment and other dimensions
        of development in one accessible platform.
        """
    )

    st.subheader("Geographic data")

    st.markdown(
        f"[Open the boundary GeoJSON]({GEOJSON_URL})"
    )

    if not map_error:
        st.write(
            f"Detected region-name property: `{detected_name_key}`"
        )
        st.write(
            f"Matched features: {len(matched_regions)}"
        )
        st.write(
            f"Skipped features: {skipped_features}"
        )

        if missing_regions:
            st.write("Unmatched regions:")
            st.write(", ".join(missing_regions))

    st.subheader("Potential indicator sources")

    sources = [
        (
            "NITI Aayog",
            "Multidimensional poverty and development reports",
            "https://www.niti.gov.in/",
        ),
        (
            "Census of India",
            "Population, literacy and demographic indicators",
            "https://censusindia.gov.in/census.website/en/data",
        ),
        (
            "Reserve Bank of India",
            "State finances, income and economic statistics",
            "https://www.rbi.org.in/",
        ),
        (
            "UDISE+",
            "School education statistics",
            "https://www.udiseplus.gov.in/",
        ),
        (
            "Open Government Data Platform",
            "Government datasets across sectors",
            "https://www.data.gov.in/",
        ),
    ]

    for source_name, description, url in sources:
        st.markdown(
            f"- **[{source_name}]({url})**: {description}"
        )

    st.subheader("Methodology and limitations")

    st.write(
        """
        Indicator values should only be added after checking their
        source, definition, reference year, geographic coverage and
        units. State comparisons can be misleading when indicators
        come from different years or use inconsistent definitions.

        The current app does not calculate a composite development
        score and does not infer missing observations.
        """
    )


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(
    "India Development Atlas | An independent data exploration project"
)
