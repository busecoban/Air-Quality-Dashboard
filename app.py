# app.py
# Antalya Live Air-Quality Dashboard
#   • Genel AQI metriği
#   • Bileşen bar grafiği
#   • Son 24 saatlik AQI çizgi grafiği
#   • Folium haritasında istasyon baloncuğu

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, cast

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from aqi_client import _get_token, fetch_aqi

CITY_ID = "antalya"           # WAQI şehir/istasyon kimliği
TOKEN = _get_token()          # ortam değişkeni veya Streamlit secrets

# ---------- Veri çekme ---------- #

@st.cache_data(ttl=600)       # 10 dk önbellek
def fetch_live() -> tuple[datetime, int, Dict[str, float], float, float]:
    """API'den zaman damgası, AQI, bileşenler, enlem/boylam döndür."""
    raw = fetch_aqi(CITY_ID, TOKEN)
    ts = datetime.fromtimestamp(raw["data"]["time"]["v"])
    aqi = raw["data"]["aqi"]
    comps = {k.upper(): v["v"] for k, v in raw["data"].get("iaqi", {}).items()}
    lat, lon = raw["data"]["city"]["geo"]
    return ts, aqi, comps, lat, lon


# ---------- Oturum içi geçmiş ---------- #

if "history" not in st.session_state:
    st.session_state["history"] = []  # type: ignore[assignment]

ts, aqi, comps, lat, lon = fetch_live()

history: List[Dict[str, int]] = cast(List[Dict[str, int]], st.session_state["history"])
if not history or history[-1]["ts"] != int(ts.timestamp()):
    history.append({"ts": int(ts.timestamp()), "aqi": aqi})

hist_df = pd.DataFrame(history)
hist_df["ts"] = pd.to_datetime(hist_df["ts"])
last_24h = hist_df[hist_df["ts"] >= datetime.utcnow() - timedelta(hours=24)]

# ---------- Streamlit arayüzü ---------- #

st.set_page_config(page_title="Antalya AQI", page_icon="🌬️", layout="wide")
col1, col2 = st.columns([1, 2])

with col1:
    st.title("🌬️ Antalya Hava Kalitesi – Canlı")
    st.metric("Genel AQI", aqi, help=f"Son güncelleme: {ts:%d %b %Y %H:%M}")
    st.subheader("Bileşenler (µg/m³)")
    st.bar_chart(
        pd.DataFrame(comps.items(), columns=["Component", "Value"]).set_index("Component")
    )

with col2:
    st.subheader("Son 24 Saatlik AQI Değişimi")
    if len(last_24h) > 1:
        st.line_chart(last_24h.set_index("ts")[["aqi"]])
    else:
        st.info("24 saatlik trend için veri birikiyor…")

# ---------- Folium haritası ---------- #

def aqi_color(val: int) -> str:
    """AQI değerine uygun renk döndür (EPA skalası)."""
    if val <= 50:
        return "#009966"      # Good
    elif val <= 100:
        return "#ffde33"      # Moderate
    elif val <= 150:
        return "#ff9933"      # Unhealthy for SG
    elif val <= 200:
        return "#cc0033"      # Unhealthy
    elif val <= 300:
        return "#660099"      # Very Unhealthy
    else:
        return "#7e0023"      # Hazardous

fol_map = folium.Map(location=[lat, lon], zoom_start=11, control_scale=True)
folium.CircleMarker(
    location=[lat, lon],
    radius=12,
    color=aqi_color(aqi),
    fill=True,
    fill_color=aqi_color(aqi),
    fill_opacity=0.75,
    popup=f"Antalya AQI: {aqi}",
).add_to(fol_map)

st.subheader("İstasyon Konumu")
st_folium(fol_map, height=400, width=700)

st.caption(
    "Kaynak: WAQI • Veri 10 dakikada bir yenilenir. "
    "24 saatlik veri yalnızca oturum süresince saklanır."
)
