import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard", layout="wide")

st.title("Project Dashboard")

# Dataset di esempio temporaneo
df = px.data.iris()

st.subheader("Dataset Preview")
st.dataframe(df.head())

st.subheader("Simple Plot")
fig = px.scatter(
    df,
    x="sepal_width",
    y="sepal_length",
    color="species"
)

st.plotly_chart(fig, use_container_width=True)
