# app.py – Türkiye AQI Dashboard (Multi‑City) – Gauge UI v2
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, cast

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_folium import st_folium

from aqi_client import _get_token, fetch_aqi

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
TOKEN = _get_token()
CACHE_TTL = 600  # 10 dk

CITY_MAP: Dict[str, str] = {
    "Antalya": "antalya",
    "Muğla": "mugla",
    "İstanbul": "istanbul",
    "Ankara": "ankara",
    "İzmir": "izmir",
    "Bursa": "bursa",
    "Adana": "adana",
    "Trabzon": "trabzon",
    "Gaziantep": "gaziantep",
}

COLORS = [
    (0, 50, "#009966", "İyi"),
    (51, 100, "#ffde33", "Orta"),
    (101, 150, "#ff9933", "Duyarlı"),
    (151, 200, "#cc0033", "Sağlıksız"),
    (201, 300, "#660099", "Çok Sağlıksız"),
    (301, 500, "#7e0023", "Tehlikeli"),
]

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def aqi_color(val: int) -> str:
    for low, high, clr, _ in COLORS:
        if low <= val <= high:
            return clr
    return "#7e0023"

@st.cache_data(ttl=CACHE_TTL)
def fetch_live(city_id: str) -> tuple[datetime, int, Dict[str, float], float, float]:
    raw = fetch_aqi(city_id, TOKEN)
    ts = datetime.fromtimestamp(raw["data"]["time"]["v"])
    aqi_val = raw["data"]["aqi"]
    comps = {k.upper(): v["v"] for k, v in raw["data"].get("iaqi", {}).items()}
    lat, lon = raw["data"]["city"]["geo"]
    return ts, aqi_val, comps, lat, lon

# ------------------------------------------------------------------
# Page & CSS
# ------------------------------------------------------------------

st.set_page_config(page_title="Türkiye AQI Dashboard", page_icon="🌬️", layout="wide")

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {background:#f4f7fb;padding-top:1.2rem;width:235px !important;}
    .sidebar-title {font-size:1.2rem;font-weight:600;margin-bottom:0.6rem;}
    .sidebar-label {color:#6c6c6c;font-size:0.85rem;margin:0;}
    .sidebar-value {font-weight:600;margin-bottom:0.8rem;}
    main > div.block-container {padding-top:0.5rem;padding-bottom:0rem;}
    h1,h2,h3 {margin-top:0.25rem;margin-bottom:0.6rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# Sidebar & data fetch
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("<div class='sidebar-title'>🌬️ AQI Dashboard</div>", unsafe_allow_html=True)
    city_name = st.selectbox("Şehir seç", list(CITY_MAP.keys()), index=0)
    city_id = CITY_MAP[city_name]

try:
    ts, aqi, comps, lat, lon = fetch_live(city_id)
except Exception as e:
    st.error(f"API hatası: {e}")
    st.stop()

with st.sidebar:
    st.markdown(f"<p class='sidebar-label'>İstasyon</p><p class='sidebar-value'>{city_name}</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='sidebar-label'>Son güncelleme</p><p class='sidebar-value'>{ts:%d %b %Y %H:%M}</p>", unsafe_allow_html=True)
    if not TOKEN:
        st.warning("WAQI_TOKEN bulunamadı!", icon="⚠️")

# ------------------------------------------------------------------
# Session‑based history per city (flat line fallback remains)
# ------------------------------------------------------------------
key_hist = f"history_{city_id}"
if key_hist not in st.session_state:
    st.session_state[key_hist] = []  # type: ignore[assignment]
history: List[Dict[str, int]] = cast(List[Dict[str, int]], st.session_state[key_hist])
if not history or history[-1]["ts"] != ts:
    history.append({"ts": ts, "aqi": aqi})

hist_df = pd.DataFrame(history)
hist_df["ts"] = pd.to_datetime(hist_df["ts"])
# --- flat fill for first visit
if len(hist_df) < 2:
    rng = pd.date_range(end=ts, periods=24, freq="h")
    hist_df = pd.DataFrame({"ts": rng, "aqi": aqi})

# ------------------------------------------------------------------
# KPI cards
# ------------------------------------------------------------------
col_aqi, col_pm25, col_pm10 = st.columns(3)
col_aqi.metric("AQI", aqi)
col_pm25.metric("PM 2.5", f"{comps.get('PM2.5', 0):.1f}")
col_pm10.metric("PM 10", f"{comps.get('PM10', 0):.1f}")
style_metric_cards(background_color="#FFFFFF22", border_size_px=0.5, box_shadow=True)

# ------------------------------------------------------------------
# Gauge + Bar charts
# ------------------------------------------------------------------
chart_col, bar_col = st.columns([1.2, 1])

# ---------- Gauge (Full‑circle speedometer) ----------
with chart_col:
    st.subheader("AQI Seviye Göstergesi")

    # Simple semicircle gauge using Plotly Indicator
    steps_cfg = [{"range": [low, high], "color": clr} for low, high, clr, _ in COLORS]
    gauge_fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=aqi,
            number={"font": {"size": 36}},
            gauge={
                "axis": {"range": [None, 500]},
                "bar": {"color": aqi_color(aqi)},
                "steps": steps_cfg,
            },
        )
    )
    gauge_fig.update_layout(margin=dict(l=20, r=20, t=10, b=10), height=250)
    st.plotly_chart(gauge_fig, use_container_width=True)

    # Legend under gauge
    legend_html = "<div style='display:flex;flex-wrap:wrap;gap:12px;font-size:0.75rem;'>"
    for low, high, clr, name in COLORS:
        rng = f"{low}-{high}" if high < 500 else f"{low}+"
        legend_html += (
            f"<span style='display:flex;align-items:center;'>"
            f"<span style='width:12px;height:12px;background:{clr};display:inline-block;margin-right:4px;border-radius:2px;'></span>"
            f"{name} ({rng})"
            "</span>"
        )
    legend_html += "</div>"
    st.markdown(legend_html, unsafe_allow_html=True)

# ---------- Components bar ---------- ----------
with bar_col:
    st.subheader("Bileşen Dağılımı (µg/m³)")
    comp_df = pd.DataFrame(comps.items(), columns=["Cmp", "Val"]).sort_values("Val", ascending=False)
    bar_fig = px.bar(comp_df, x="Cmp", y="Val", color="Val", color_continuous_scale="thermal")
    bar_fig.update_layout(coloraxis_showscale=False, yaxis_title=None,
                          plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(bar_fig, use_container_width=True)

# ------------------------------------------------------------------
# Map
# ------------------------------------------------------------------
# ------------------------------------------------------------------

st.markdown("### 🗺️ İstasyon Konumu")
map_obj = folium.Map(location=[lat, lon], zoom_start=11, control_scale=True)
folium.CircleMarker(
    location=[lat, lon], radius=12, color=aqi_color(aqi), fill=True,
    fill_color=aqi_color(aqi), fill_opacity=0.85, popup=f"{city_name} AQI: {aqi}"
).add_to(map_obj)

st_folium(map_obj, height=550, width="100%")
