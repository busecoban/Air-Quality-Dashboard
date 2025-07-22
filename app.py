# app.py  –  Antalya AQI Dashboard 2.2 (Refined Sidebar)
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, cast

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_folium import st_folium

from aqi_client import _get_token, fetch_aqi

CITY_ID = "antalya"
TOKEN = _get_token()
CACHE_TTL = 600

st.set_page_config(page_title="Antalya AQI", page_icon="🌬️", layout="wide")

# ---------------- Custom CSS -----------------
st.markdown(
    """
    <style>
/* Sidebar */
section[data-testid="stSidebar"] {
  background-color: #f4f7fb;
  padding-top: 1.5rem;
  width: 220px !important;  /* slightly slimmer */
}
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
  padding: 0 0.5rem;
}
.sidebar-title {font-size:1.2rem;font-weight:600;margin-bottom:0.4rem;}
.sidebar-label {color:#6c6c6c;font-size:0.85rem;margin:0;}
.sidebar-value {font-weight:600;margin-bottom:0.6rem;}

/* Main container spacing */
main > div.block-container {padding-top:0.5rem;padding-bottom:0rem;}

/* Headings & element gaps */
h1,h2,h3 {margin-top:0.25rem;margin-bottom:0.6rem;}
.element-container:has(div[data-testid="stMetric"]){margin-bottom:0.6rem;}

</style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Helpers --------------------

def aqi_color(val: int) -> str:
    if val <= 50:
        return "#009966"
    elif val <= 100:
        return "#ffde33"
    elif val <= 150:
        return "#ff9933"
    elif val <= 200:
        return "#cc0033"
    elif val <= 300:
        return "#660099"
    return "#7e0023"

@st.cache_data(ttl=CACHE_TTL)
def fetch_live() -> tuple[datetime, int, Dict[str, float], float, float]:
    raw = fetch_aqi(CITY_ID, TOKEN)
    ts = datetime.fromtimestamp(raw["data"]["time"]["v"])
    aqi_val = raw["data"]["aqi"]
    comps = {k.upper(): v["v"] for k, v in raw["data"].get("iaqi", {}).items()}
    lat, lon = raw["data"]["city"]["geo"]
    return ts, aqi_val, comps, lat, lon

# ---------------- Fetch + history -------------

ts, aqi, comps, lat, lon = fetch_live()
if "history" not in st.session_state:
    st.session_state["history"] = []  # type: ignore[assignment]
history: List[Dict[str, int]] = cast(List[Dict[str, int]], st.session_state["history"])
if not history or history[-1]["ts"] != ts:
    history.append({"ts": ts, "aqi": aqi})

hist_df = pd.DataFrame(history)
hist_df["ts"] = pd.to_datetime(hist_df["ts"])
last24 = hist_df[hist_df["ts"] >= datetime.utcnow() - timedelta(hours=24)]

# ---------------- Sidebar ---------------------
with st.sidebar:
    st.markdown("<div class='sidebar-title'>🌬️ AQI Dashboard</div>", unsafe_allow_html=True)
    st.markdown(
        f"<p class='sidebar-label'>İstasyon</p><p class='sidebar-value'>{CITY_ID}</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p class='sidebar-label'>Son güncelleme</p><p class='sidebar-value'>{ts:%d %b %Y  %H:%M}</p>",
        unsafe_allow_html=True,
    )
    if not TOKEN:
        st.warning("WAQI_TOKEN bulunamadı!", icon="⚠️")

# ---------------- KPI Row ---------------------
col_aqi, col_pm25, col_pm10 = st.columns(3)
col_aqi.metric("AQI", aqi)
col_pm25.metric("PM 2.5", f"{comps.get('PM2.5', 0):.1f}")
col_pm10.metric("PM 10", f"{comps.get('PM10', 0):.1f}")
style_metric_cards(background_color="#FFFFFF22", border_size_px=0.5, box_shadow=True)

# ---------------- Charts ----------------------
chart_col, bar_col = st.columns([2, 1.3])

with chart_col:
    st.subheader("Son 24 Saat AQI Trend")
    if len(last24) > 1:
        line = px.line(last24, x="ts", y="aqi", markers=True, line_color=aqi_color(aqi))
        line.update_layout(margin=dict(l=0, r=0, t=30, b=0), xaxis_title=None, yaxis_title="AQI")
        st.plotly_chart(line, use_container_width=True)
    else:
        st.info("Trend grafiği için veri birikiyor…")

with bar_col:
    st.subheader("Bileşen Dağılımı (µg/m³)")
    comp_df = (
        pd.DataFrame(comps.items(), columns=["Cmp", "Val"]).sort_values("Val", ascending=False)
    )
    bar = px.bar(comp_df, x="Cmp", y="Val", color="Val", color_continuous_scale="thermal")
    bar.update_layout(coloraxis_showscale=False, yaxis_title=None, plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(bar, use_container_width=True)

# ---------------- Map -------------------------

st.markdown("### 🗺️ İstasyon Konumu")
fol_map = folium.Map(location=[lat, lon], zoom_start=11, control_scale=True)
folium.CircleMarker(
    location=[lat, lon],
    radius=12,
    color=aqi_color(aqi),
    fill=True,
    fill_color=aqi_color(aqi),
    fill_opacity=0.8,
    popup=f"AQI: {aqi}",
).add_to(fol_map)

st_folium(fol_map, height=550, width="100%")
