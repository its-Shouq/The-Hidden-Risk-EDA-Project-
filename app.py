"""THE HIDDEN RISK — polished FAA wildlife strike dashboard.

Run with:
    streamlit run app.py
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from lab import add_group, build_lab_html, lab_payload

ROOT = Path(__file__).resolve().parent
st.set_page_config(
    page_title="THE HIDDEN RISK | FAA Wildlife Strikes",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown((ROOT / "style.css").read_text(encoding="utf-8"), unsafe_allow_html=True)

INK = "#EAF2F7"
BLUE = "#7CB7DE"
GOLD = "#F1B75A"
MUTED = "#92A8B8"
GRID = "#244155"
PHASES = ["Approach", "Climb", "En Route", "Landing Roll", "Take-off Run"]
SIZES = ["Small", "Medium", "Large"]
GROUPS = ["Single", "Multiple"]


@st.cache_data(show_spinner="Loading FAA reports...")
def read_csv(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path, low_memory=False)
    needed = [
        "INCIDENT_YEAR",
        "INCIDENT_MONTH",
        "SPECIES",
        "SIZE",
        "PHASE_OF_FLIGHT",
        "STRIKE_GROUP",
        "INDICATED_DAMAGE",
    ]
    missing = set(needed) - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    data["INDICATED_DAMAGE"] = pd.to_numeric(data["INDICATED_DAMAGE"], errors="raise")
    if not data["INDICATED_DAMAGE"].isin([0, 1]).all():
        raise ValueError("INDICATED_DAMAGE must contain only 0 and 1")
    data["INCIDENT_YEAR"] = pd.to_numeric(data["INCIDENT_YEAR"], errors="raise").astype(int)
    data["INCIDENT_MONTH"] = pd.to_numeric(data["INCIDENT_MONTH"], errors="raise").astype(int)
    if not data["INCIDENT_MONTH"].between(1, 12).all():
        raise ValueError("Invalid month values")
    for name in ["SPECIES", "SIZE", "PHASE_OF_FLIGHT", "STRIKE_GROUP"]:
        data[name] = data[name].fillna("Not recorded").astype(str)
    return data


try:
    df = add_group(read_csv(ROOT / "FAA_Cleaned.csv"))
except (FileNotFoundError, ValueError, OSError, pd.errors.ParserError) as exc:
    st.error(f"Could not load FAA_Cleaned.csv: {exc}")
    st.stop()


@st.cache_data(show_spinner=False)
def species_table(data: pd.DataFrame, threshold: int = 100) -> pd.DataFrame:
    selected = data.loc[
        ~data["SPECIES"].str.contains("Unknown", case=False, na=False)
        & data["SPECIES"].ne("Not recorded")
    ]
    result = selected.groupby("SPECIES")["INDICATED_DAMAGE"].agg(["count", "sum", "mean"]).reset_index()
    result.columns = ["Species", "Reports", "Damaging", "Rate"]
    result["Rate"] *= 100
    return result[result["Reports"] >= threshold]


def grouped(data: pd.DataFrame, column: str) -> pd.DataFrame:
    return data.groupby(column)["INDICATED_DAMAGE"].agg(["count", "sum", "mean"])


def plot_style(fig: go.Figure, h: int = 340) -> go.Figure:
    fig.update_layout(
        height=h,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK, size=13, family="Inter, Segoe UI, sans-serif"),
        margin=dict(l=12, r=34, t=48, b=38),
        showlegend=False,
        hoverlabel=dict(bgcolor="#132738", font_color=INK),
        xaxis=dict(gridcolor=GRID, zeroline=False),
        yaxis=dict(gridcolor=GRID, zeroline=False),
    )
    return fig


def section(label: str, headline: str, intro: str = "") -> None:
    st.markdown(
        f'<div class="eyebrow">{escape(label)}</div>'
        f'<h2 class="section-heading">{escape(headline)}</h2>'
        + (f'<p class="section-intro">{escape(intro)}</p>' if intro else ""),
        unsafe_allow_html=True,
    )


def kpi(name: str, val: str, desc: str, tone: str = "") -> None:
    st.markdown(
        f'<div class="kpi {tone}"><div class="kpi-name">{escape(name)}</div>'
        f'<div class="kpi-number">{escape(val)}</div>'
        f'<div class="kpi-desc">{escape(desc)}</div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# FILTERS (main page instead of sidebar)
# ---------------------------------------------------------------------------
st.markdown(
    """
<div class="topbar">
  <div class="brandline">FAA Wildlife Strikes · 2020–2025</div>
  <div class="navtext">Explore · Compare · Simulate</div>
</div>
<div class="hero">
  <div class="hero-copy">
    <div class="hero-kicker">FAA NATIONAL WILDLIFE STRIKE DATABASE</div>
    <h1>THE HIDDEN RISK</h1>
    <div class="hero-sub">Not every strike is equal.</div>
    <p>This dashboard compares how often wildlife strikes are reported with how often those reports involve aircraft damage.</p>
    <div class="hero-tags"><span>110,940 FAA REPORTS</span><span>INTERACTIVE DASHBOARD</span><span>DATA-DRIVEN SIMULATION</span></div>
  </div>
  <div class="hero-radar">
      <div class="radar-ring ring-a"></div>
      <div class="radar-ring ring-b"></div>
      <div class="radar-ring ring-c"></div>
      <div class="radar-cross"></div>
      <div class="radar-plane">✈</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.expander("Data source and filters", expanded=False):
    st.markdown(
        '<div class="filter-intro">Source: FAA National Wildlife Strike Database. '
        'Filters update every KPI, chart, and simulation rate shown below.</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1.15, 1, 1], gap="medium")
    with c1:
        years = st.slider(
            "Incident years",
            int(df.INCIDENT_YEAR.min()),
            int(df.INCIDENT_YEAR.max()),
            (int(df.INCIDENT_YEAR.min()), int(df.INCIDENT_YEAR.max())),
        )
    with c2:
        size_choice = st.selectbox("Animal size", ["All sizes", *SIZES, "Not recorded"], index=0)
    with c3:
        phase_options = sorted(df.PHASE_OF_FLIGHT.unique().tolist())
        selected_phases = st.multiselect(
            "Flight phases",
            phase_options,
            default=[],
            placeholder="All phases",
        )
    st.caption(
        "The dashboard uses counts and recorded damage among reported strikes; it does not measure risk per flight."
    )

filtered = df.loc[df.INCIDENT_YEAR.between(*years)]
if size_choice != "All sizes":
    filtered = filtered.loc[filtered.SIZE.eq(size_choice)]
if selected_phases:
    filtered = filtered.loc[filtered.PHASE_OF_FLIGHT.isin(selected_phases)]

if filtered.empty:
    st.warning("No records match this selection. Adjust the filters in the panel above.")
    st.stop()

rank = species_table(filtered)
total = len(filtered)
damaging = int(filtered.INDICATED_DAMAGE.sum())
damage_rate = damaging / total * 100
known_size_share = filtered.SIZE.ne("Not recorded").mean() * 100
phase_label = ", ".join(selected_phases) if selected_phases else "All phases"
size_label = size_choice
st.markdown(
    f'<div class="selection-strip">Showing <strong>{total:,}</strong> reports · '
    f'Years <strong>{years[0]}–{years[1]}</strong> · '
    f'Size <strong>{escape(size_label)}</strong> · '
    f'Flight phase <strong>{escape(phase_label)}</strong></div>',
    unsafe_allow_html=True,
)

# Summary statistics
row = st.columns(4, gap="medium")
with row[0]:
    kpi("Reported strikes", f"{total:,}", "Reports in current selection")
with row[1]:
    kpi("Damaging reports", f"{damaging:,}", "With recorded aircraft damage")
with row[2]:
    kpi("Recorded damage rate", f"{damage_rate:.2f}%", "Damaging reports ÷ reported strikes", "amber")
with row[3]:
    kpi("Known animal size", f"{known_size_share:.1f}%", "Share with recorded size")

st.markdown('<div class="story-divider"></div>', unsafe_allow_html=True)

# 01 Hook
section("01 / FIRST IMPRESSION", "Predict before the reveal", "Which category has the higher recorded damage rate?")
cols = {row.Species: row for row in rank.itertuples(index=False)}
if "Mourning dove" in cols and "White-tailed deer" in cols:
    dove = cols["Mourning dove"]
    deer = cols["White-tailed deer"]
    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown(
            f'<div class="versus-card blue"><div class="versus-label">MOST REPORTED EXAMPLE</div>'
            f'<h3>Mourning dove</h3><div class="versus-number">{dove.Reports:,}</div>'
            '<div class="versus-small">reported strikes</div></div>',
            unsafe_allow_html=True,
        )
        if st.button("Predict Mourning dove", key="guess_dove", use_container_width=True):
            st.session_state["guess"] = "Mourning dove"
    with right:
        st.markdown(
            f'<div class="versus-card amber"><div class="versus-label">LESS FREQUENT EXAMPLE</div>'
            f'<h3>White-tailed deer</h3><div class="versus-number">{deer.Reports:,}</div>'
            '<div class="versus-small">reported strikes</div></div>',
            unsafe_allow_html=True,
        )
        if st.button("Predict White-tailed deer", key="guess_deer", use_container_width=True):
            st.session_state["guess"] = "White-tailed deer"

    guess = st.session_state.get("guess")
    if guess:
        correct = guess == "White-tailed deer"
        st.markdown(
            f'<div class="reveal"><span class="reveal-kicker">'
            f'{"YOU GOT IT" if correct else "SURPRISE"}</span>'
            '<div class="reveal-head">Frequency does not tell the whole story.</div>'
            '<div class="reveal-two">'
            f'<div>Mourning dove <strong>{dove.Rate:.2f}%</strong>'
            f'<small>{int(dove.Damaging):,} damaging reports</small></div>'
            f'<div>White-tailed deer <strong class="gold">{deer.Rate:.2f}%</strong>'
            f'<small>{int(deer.Damaging):,} damaging reports</small></div>'
            '</div></div>',
            unsafe_allow_html=True,
        )
else:
    st.info("The featured animal comparison needs a wider selection. Reset the filters to see the full reveal.")

st.markdown('<div class="story-divider"></div>', unsafe_allow_html=True)

# 02 Ranking explorer
section(
    "02 / THE RANKING FLIP",
    "Watch the ranking change",
    "Blue bars rank wildlife by number of reports. Amber bars rank them by recorded damage rate.",
)
if not rank.empty:
    left, right = st.columns([1.8, 1], gap="medium")
    with left:
        metric = st.radio("Compare by", ["Number of reports", "Damage rate (%)"], horizontal=True, key="rank_metric")
    with right:
        top_n = st.select_slider("Categories shown", [5, 8, 10, 12, 15], value=10)

    is_count = metric == "Number of reports"
    metric_col = "Reports" if is_count else "Rate"
    chart_color = BLUE if is_count else GOLD
    status_text = "Most frequently reported" if is_count else "Highest recorded damage rate"
    status_note = (
        "Sorted by number of reports · unit: reports"
        if is_count
        else "Sorted by damage rate · unit: % of reports with damage"
    )
    st.markdown(
        f'<div class="mode-banner {"count" if is_count else "rate"}">'
        f'<div class="mode-kicker">Current ranking mode</div>'
        f'<div class="mode-title">{status_text}</div>'
        f'<div class="mode-note">{status_note}</div></div>',
        unsafe_allow_html=True,
    )
    rankshown = rank.nlargest(top_n, metric_col).sort_values(metric_col)
    fig = go.Figure(
        go.Bar(
            x=rankshown[metric_col],
            y=rankshown.Species,
            orientation="h",
            marker=dict(color=chart_color, line=dict(width=0)),
            text=rankshown[metric_col].map(lambda v: f"{v:,.0f}" if is_count else f"{v:.2f}%"),
            textposition="outside",
            customdata=rankshown[["Reports", "Damaging", "Rate"]].to_numpy(),
            hovertemplate="%{y}<br>Reports: %{customdata[0]:,}<br>Damaging: %{customdata[1]:,}<br>Damage rate: %{customdata[2]:.2f}%<extra></extra>",
        )
    )
    plot_style(fig, max(390, 48 * len(rankshown)))
    fig.update_layout(
        xaxis=dict(title=metric, range=[0, float(rankshown[metric_col].max()) * 1.18]),
        yaxis=dict(title="", automargin=True),
        transition=dict(duration=500),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="ranking_chart")
    st.markdown('<div class="microcaption">Eligible categories have at least 100 reports in the current selection.</div>', unsafe_allow_html=True)

    with st.expander("Compare two wildlife categories", expanded=False):
        options = sorted(rank.Species.tolist())
        ix1 = options.index("Mourning dove") if "Mourning dove" in options else 0
        ix2 = options.index("White-tailed deer") if "White-tailed deer" in options else min(1, len(options) - 1)
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            one = st.selectbox("Category A", options, index=ix1)
        with c2:
            two = st.selectbox("Category B", options, index=ix2)
        if one != two:
            pair = rank[rank.Species.isin([one, two])].copy()
            p1, p2 = st.columns(2, gap="medium")
            with p1:
                fig2 = go.Figure(
                    go.Bar(
                        x=pair["Reports"], y=pair.Species, orientation="h", marker_color=BLUE,
                        text=pair["Reports"].map(lambda z: f"{z:,.0f}"), textposition="outside"
                    )
                )
                plot_style(fig2, 270)
                fig2.update_layout(title="Reported strikes", xaxis=dict(range=[0, float(pair["Reports"].max()) * 1.22]), yaxis=dict(title="", automargin=True))
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            with p2:
                fig3 = go.Figure(
                    go.Bar(
                        x=pair["Rate"], y=pair.Species, orientation="h", marker_color=GOLD,
                        text=pair["Rate"].map(lambda z: f"{z:.2f}%"), textposition="outside"
                    )
                )
                plot_style(fig3, 270)
                fig3.update_layout(title="Damage rate (%)", xaxis=dict(range=[0, float(pair["Rate"].max()) * 1.22]), yaxis=dict(title="", automargin=True))
                st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
else:
    st.info("No wildlife category reaches the 100-report threshold under this filter selection.")

st.markdown('<div class="story-divider"></div>', unsafe_allow_html=True)

# 03 Simulation
section(
    "03 / INCIDENT LAB",
    "Explore a wildlife strike scenario",
    "Choose an exact FAA species, or select a heatmap cell to load a scenario.",
)
components.html(build_lab_html(lab_payload(filtered)), height=953, scrolling=False)

st.markdown('<div class="story-divider"></div>', unsafe_allow_html=True)

# 04 Size and strike group
section(
    "04 / PATTERNS THAT MATTER",
    "Frequency is not the same as damage rate",
    "Use this section to compare how often groups appear versus how often they involve recorded damage.",
)
size_stats = grouped(filtered, "SIZE").reindex([*SIZES, "Not recorded"]).fillna(0)
known_size_stats = size_stats.reindex(SIZES).fillna(0)
col_a, col_b = st.columns(2, gap="medium")
with col_a:
    fig = go.Figure(
        go.Bar(
            x=size_stats.index.tolist(),
            y=size_stats["count"],
            marker_color=BLUE,
            text=size_stats["count"].astype(int).map(lambda n: f"{n:,}"),
            textposition="outside",
        )
    )
    plot_style(fig, 340)
    fig.update_layout(title="Reported strikes by animal size", yaxis=dict(title="Reports", rangemode="tozero"))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
with col_b:
    fig = go.Figure(
        go.Bar(
            x=known_size_stats.index.tolist(),
            y=known_size_stats["mean"] * 100,
            marker_color=GOLD,
            text=(known_size_stats["mean"] * 100).map(lambda n: f"{n:.2f}%"),
            textposition="outside",
        )
    )
    plot_style(fig, 340)
    fig.update_layout(title="Recorded damage rate by known animal size", yaxis=dict(title="Damage rate (%)", rangemode="tozero"))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

sg_stats = grouped(filtered[filtered.STRIKE_GROUP.isin(GROUPS)], "STRIKE_GROUP").reindex(GROUPS).fillna(0)
single = float(sg_stats.loc["Single", "mean"] * 100) if "Single" in sg_stats.index else 0.0
multiple = float(sg_stats.loc["Multiple", "mean"] * 100) if "Multiple" in sg_stats.index else 0.0
ratio = multiple / single if single else float("nan")
st.markdown(
    f'<div class="one-line-insight"><span>Single vs multiple strikes</span>'
    f'<b>{single:.2f}%</b><i>vs</i><b class="warm">{multiple:.2f}%</b>'
    + (f'<strong>≈ {ratio:.1f}×</strong>' if pd.notna(ratio) else '<strong>—</strong>')
    + '</div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="story-divider"></div>', unsafe_allow_html=True)

# 05 Annual trends
section(
    "05 / YEARLY VIEW",
    "Counts rose — but what happened to rates?",
    "Recorded damage among reported strikes, year by year.",
)
annual = grouped(filtered, "INCIDENT_YEAR").reset_index()
annual["rate"] = annual["mean"] * 100
# The notebook's annual view is the recorded damage rate by year.
# Report counts are already summarized above, so keep this section focused.
fig = go.Figure(
    go.Scatter(
        x=annual.INCIDENT_YEAR.tolist(),
        y=annual["rate"].tolist(),
        mode="lines+markers+text",
        line=dict(color=GOLD, width=4),
        marker=dict(size=10, color=GOLD),
        text=[f"{v:.2f}%" for v in annual["rate"].tolist()],
        textposition="top center",
        hovertemplate="Year: %{x}<br>Damage rate: %{y:.2f}%<extra></extra>",
    )
)
plot_style(fig, 355)
fig.update_layout(
    title="Annual recorded damage rate",
    xaxis=dict(title="Year", tickmode="array", tickvals=annual.INCIDENT_YEAR.tolist()),
    yaxis=dict(title="Damage rate (%)", range=[0, max(5.0, float(annual["rate"].max()) * 1.2)]),
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="annual_chart")

st.markdown('<div class="story-divider"></div>', unsafe_allow_html=True)

# 06 Insights
section("06 / KEY TAKEAWAYS", "Three findings worth remembering")
findings = [
    ("01", "SIZE", "Large animals stand out", "Among known sizes, larger animals show higher recorded damage rates than smaller animals."),
    ("02", "FREQUENCY", "The ranking reverses", "The most reported wildlife category is not necessarily the one with the highest damage rate."),
    ("03", "CONTEXT", "Circumstances matter", "Recorded damage rates vary by flight phase and by whether one or multiple animals were involved."),
]
cols = st.columns(3, gap="medium")
for col, (n, tag, title_text, body_text) in zip(cols, findings):
    with col:
        st.markdown(
            f'<div class="insight"><div class="insight-n">{n} / {tag}</div>'
            f'<h3>{escape(title_text)}</h3><p>{escape(body_text)}</p></div>',
            unsafe_allow_html=True,
        )

st.markdown('<div class="story-divider"></div>', unsafe_allow_html=True)

# Data preview
with st.expander("Data preview", expanded=False):
    preview_cols = [
        c
        for c in [
            "INCIDENT_DATE",
            "INCIDENT_YEAR",
            "SPECIES",
            "SIZE",
            "PHASE_OF_FLIGHT",
            "STRIKE_GROUP",
            "INDICATED_DAMAGE",
        ]
        if c in filtered.columns
    ]
    st.caption("Preview of the current filtered data.")
    st.dataframe(filtered[preview_cols].head(30), use_container_width=True, hide_index=True, height=285)

st.markdown(
    '<div class="footer">THE HIDDEN RISK <span>◆</span> FAA NATIONAL WILDLIFE STRIKE DATABASE <span>◆</span> 2020–2025</div>',
    unsafe_allow_html=True,
)
