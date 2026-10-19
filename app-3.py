
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="India Development Atlas",
    page_icon="🇮🇳",
    layout="wide"
)

data = {
    "State": [
        "Tamil Nadu", "Kerala", "Karnataka", "Maharashtra",
        "Gujarat", "Telangana", "Andhra Pradesh", "Punjab",
        "Haryana", "Rajasthan", "Uttar Pradesh", "Bihar",
        "West Bengal", "Odisha", "Madhya Pradesh", "Jharkhand",
        "Chhattisgarh", "Assam", "Himachal Pradesh", "Uttarakhand"
    ],
    "Development Score": [
        78, 86, 76, 79, 74, 75, 70, 77, 76, 62,
        54, 42, 65, 59, 53, 47, 55, 57, 81, 73
    ],
    "Education Score": [
        80, 91, 78, 77, 73, 76, 72, 79, 75, 60,
        53, 41, 68, 61, 54, 46, 56, 58, 83, 76
    ],
    "Healthcare Score": [
        76, 89, 72, 75, 70, 73, 69, 76, 74, 61,
        52, 43, 66, 58, 52, 48, 54, 56, 82, 74
    ]
}

df = pd.DataFrame(data)

st.title("India Development Atlas")
st.caption(
    "Explore regional development and socioeconomic disparities "
    "| Prototype with illustrative data"
)

st.warning(
    "Demonstration only: scores are fictional and must not be "
    "interpreted as actual state development statistics."
)

indicator = st.sidebar.selectbox(
    "Choose an indicator",
    ["Development Score", "Education Score", "Healthcare Score"]
)

left, right = st.columns(2)

with left:
    st.metric("States in prototype", len(df))

with right:
    st.metric("Average illustrative score", f"{df[indicator].mean():.1f}/100")

fig = px.bar(
    df.sort_values(indicator),
    x=indicator,
    y="State",
    orientation="h",
    color=indicator,
    color_continuous_scale="Teal",
    range_color=[0, 100],
    title=f"{indicator} by state"
)

fig.update_layout(
    height=650,
    template="plotly_white",
    xaxis_title="Illustrative score",
    yaxis_title=""
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Compare two states")

col1, col2 = st.columns(2)

with col1:
    state_a = st.selectbox(
        "First state",
        sorted(df["State"].tolist()),
        index=15
    )

with col2:
    state_b = st.selectbox(
        "Second state",
        sorted(df["State"].tolist()),
        index=9
    )

a = df.loc[df["State"] == state_a, indicator].iloc[0]
b = df.loc[df["State"] == state_b, indicator].iloc[0]

c1, c2, c3 = st.columns(3)
c1.metric(state_a, f"{a}/100")
c2.metric(state_b, f"{b}/100")
c3.metric("Absolute difference", f"{abs(a-b)} points")

st.subheader("Explore the data")
st.dataframe(df, use_container_width=True, hide_index=True)

st.download_button(
    "Download demonstration dataset",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="india_development_atlas_demo.csv",
    mime="text/csv"
)

st.caption(
    "Future releases will use sourced official data, with reference "
    "years, definitions and source links for every indicator."
)
