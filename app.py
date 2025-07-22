import pandas as pd
import streamlit as st
from datetime import datetime

# Internal import from the same repo
from aqi_client import fetch_aqi, _get_token

CITY_ID = "antalya"  # you can change to a station id like "@4018"
TOKEN = _get_token()

@st.cache_data(ttl=600)
def get_live():
    """Fetch live AQI and return (aqi, timestamp, dataframe_with_components)."""
    raw = fetch_aqi(CITY_ID, TOKEN)
    ts = datetime.fromtimestamp(raw["data"]["time"]["v"])
    aqi = raw["data"]["aqi"]

    components = {
        k.upper(): v["v"] for k, v in raw["data"].get("iaqi", {}).items()
    }
    df = (
        pd.DataFrame(components.items(), columns=["Component", "Value"])
        .set_index("Component")
        .sort_index()
    )
    return aqi, ts, df


st.set_page_config(page_title="Antalya AQI", page_icon="🌬️", layout="centered")
st.title("🌬️ Antalya Canlı Hava Kalitesi")

try:
    aqi, ts, df = get_live()
    st.metric(
        label="Genel AQI (0‒500)",
        value=aqi,
        help=f"Son güncelleme: {ts:%d %b %Y %H:%M}",
    )
    st.subheader("Bileşenler (µg/m³)")
    st.bar_chart(df)
except Exception as err:
    st.error(f"Veri alınamadı: {err}")

st.caption("Kaynak: World Air Quality Index (WAQI) • Veri 10 dakikada bir yenilenir.")
