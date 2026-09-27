"""
Business health score web page (Streamlit)

Run from the repository root:
    streamlit run streamlit_app.py

Enter a BASEPOINT company code and PIN; the page scores that business.
Credentials are used for the scoring call only and are not stored.
"""

import json
import logging
import traceback
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from health_score.basepoint import AuthenticationError, BasepointUnavailableError
from health_score.logging_config import configure_logging
from health_score.scoring import ENGINE_VERSION
from health_score.scoring.engine import band
from health_score.service import Credentials, ScoringService
from health_score.settings import get_settings

logger = logging.getLogger(__name__)

BAND_COLOURS = {
    "Strong": "#2e7d32",
    "Healthy": "#7cb342",
    "Watch": "#f9a825",
    "Weak": "#ef6c00",
    "Distressed": "#c62828",
}


@st.cache_resource
def _service() -> ScoringService:
    settings = get_settings()
    configure_logging(settings.log_level)
    return ScoringService(settings)


def _pct(x):
    return f"{x * 100:.0f}%" if x is not None else "–"


def main() -> None:
    st.set_page_config(page_title="Business Health Score", layout="wide")
    st.title("Business Health Score")
    st.caption(f"Scores a BASEPOINT business from all the data its products hold · engine {ENGINE_VERSION}")

    with st.form("login"):
        c1, c2, c3, c4 = st.columns([2, 1, 2, 2])
        company_code = c1.text_input("Company code", placeholder="XXXX-000000")
        pin = c2.text_input("PIN", type="password")
        username = c3.text_input("Username (if required)")
        as_of = c4.date_input("As of", value=date.today(), max_value=date.today())
        submitted = st.form_submit_button("Score business", type="primary")

    if submitted:
        if not company_code or not pin:
            st.error("Enter the company code and PIN.")
        else:
            with st.spinner("Logging in and collecting data from every BASE product…"):
                try:
                    st.session_state["result"] = _service().score(
                        Credentials(company_code.strip(), pin, username or None), as_of
                    )
                except AuthenticationError as e:
                    st.session_state.pop("result", None)
                    st.error(str(e))
                except BasepointUnavailableError as e:
                    st.session_state.pop("result", None)
                    st.error(f"BASEPOINT is unavailable right now: {e}")
                except Exception as e:
                    st.session_state.pop("result", None)
                    logger.exception("Scoring failed")
                    st.error(f"Could not score this business: {type(e).__name__}: {e}")
                    with st.expander("Technical details"):
                        st.code(traceback.format_exc())

    r = st.session_state.get("result")
    if not r:
        return

    biz = r["business"]
    st.subheader(f"{biz['name']} · {biz['business_type'] or ''}")
    st.caption(
        f"Company code {biz['company_code']} · as of {r['as_of']} · products used: "
        f"{', '.join(p.title() for p in r['products_used'] or []) or 'none'} · "
        f"scored in {r['duration_seconds']}s"
    )
    if r["scored_as"]["note"]:
        st.warning(r["scored_as"]["note"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Health score",
        "–" if r["score"] is None else f"{r['score']:.0f} / 100",
        None if r["score"] is None or r["score"] == r["score_uncapped"] else f"capped from {r['score_uncapped']:.0f}",
        delta_color="off",
    )
    m2.metric("Band", r["band"])
    m3.metric("Confidence", r["confidence"])
    m4.metric("Measure weight with data", _pct(r["measure_weight_available"]))

    for w in r.get("data_warnings") or []:
        st.warning(f"Data warning — {w}")
    if r["status"] == "data_unavailable":
        st.error(
            "BASEPOINT did not return this business's sales data, so it can't be scored right now. Try again later."
        )

    for f in r["red_flags"]:
        st.error(f"**{f['flag']}** — {f['detail']} (caps the score at {f['cap']})")

    dims = pd.DataFrame(
        [
            {
                "Dimension": d["label"],
                "Weight": d["weight"],
                "Score": d["score"],
                "Measures": f"{d['measures_available']}/{d['measures_total']}",
                "Note": "no data: imputed" if d["imputed"] else "",
            }
            for d in r["dimensions"].values()
        ]
    )
    left, right = st.columns([3, 2])
    chart_data = dims.assign(Band=dims["Score"].apply(band))
    bars = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X("Score:Q", scale=alt.Scale(domain=[0, 100]), title="Score (0–100)"),
            y=alt.Y("Dimension:N", sort=None, title=None, axis=alt.Axis(labelLimit=320)),
            color=alt.Color(
                "Band:N",
                scale=alt.Scale(domain=list(BAND_COLOURS), range=list(BAND_COLOURS.values())),
                legend=alt.Legend(orient="bottom", title=None),
            ),
            tooltip=["Dimension", alt.Tooltip("Score:Q", format=".1f"), "Band"],
        )
    )
    labels = bars.mark_text(align="left", dx=4).encode(text=alt.Text("Score:Q", format=".1f"), color=alt.value("#333"))
    left.altair_chart((bars + labels).properties(height=260), width="stretch")
    right.dataframe(dims.style.format({"Weight": "{:.0%}", "Score": "{:.1f}"}), hide_index=True, width="stretch")

    d1, d2 = st.columns(2)
    d1.markdown("**Strengths**")
    for d in r["drivers"]["positive"]:
        d1.markdown(f"- {d['measure']} (score {d['score']:.0f})")
    d2.markdown("**Weaknesses**")
    for d in r["drivers"]["negative"]:
        d2.markdown(f"- {d['measure']} (score {d['score']:.0f})")

    tabs = st.tabs(["Measures", "Shops", "Aging", "Suppliers", "Data coverage", "Raw result"])

    with tabs[0]:
        measures = pd.DataFrame(r["measures"])
        for dim, info in r["dimensions"].items():
            rows = measures[measures["dimension"] == dim] if not measures.empty else measures
            with st.expander(f"{info['label']} — {info['score']:.1f}", expanded=False):
                if rows.empty:
                    st.info("No measures available for this dimension; its score is imputed.")
                    continue
                view = rows[["label", "value", "unit", "score", "weight_in_dimension", "weight_in_score", "supplier"]]
                view = view.rename(
                    columns={
                        "label": "Measure",
                        "value": "Value",
                        "unit": "Unit",
                        "score": "Score",
                        "weight_in_dimension": "Weight in dimension %",
                        "weight_in_score": "Weight in score %",
                        "supplier": "Supplier",
                    }
                )
                st.dataframe(view, hide_index=True, width="stretch")
        missing = pd.DataFrame(r["measures_not_available"])
        if not missing.empty:
            with st.expander(f"Measures without data ({len(missing)})"):
                st.dataframe(
                    missing.rename(columns={"label": "Measure", "dimension": "Dimension"})[["Measure", "Dimension"]],
                    hide_index=True,
                    width="stretch",
                )

    with tabs[1]:
        shops = pd.DataFrame(r["shops"])
        if shops.empty:
            st.info("No shops.")
        else:
            view = shops[
                [
                    "name",
                    "pos_mode",
                    "status",
                    "score",
                    "band",
                    "revenue_share",
                    "revenue_t3m",
                    "revenue_p3m",
                    "declining",
                ]
            ]
            st.dataframe(
                view.rename(
                    columns={
                        "name": "Shop",
                        "pos_mode": "Type",
                        "status": "Status",
                        "score": "Score",
                        "band": "Band",
                        "revenue_share": "Share of revenue (12m)",
                        "revenue_t3m": "Revenue last 3m",
                        "revenue_p3m": "Revenue prior 3m",
                        "declining": "Declining",
                    }
                ).style.format(
                    {
                        "Share of revenue (12m)": "{:.1%}",
                        "Score": "{:.1f}",
                        "Revenue last 3m": "{:,.0f}",
                        "Revenue prior 3m": "{:,.0f}",
                    },
                    na_rep="–",
                ),
                hide_index=True,
                width="stretch",
            )
        if r["shop_network"]:
            st.markdown(
                f"**Shop network score: {r['shop_network']['score']:.1f}** "
                f"({r['shop_network']['shops_compared']} shops compared)"
            )
            st.json(r["shop_network"]["parts"])

    with tabs[2]:
        a1, a2 = st.columns(2)
        for col, (name, buckets) in zip((a1, a2), r["aging"].items(), strict=False):
            col.markdown(f"**{name.title()}** (BASEPOINT aging report)")
            if buckets:
                col.dataframe(
                    pd.DataFrame(buckets.items(), columns=["Bucket", "Amount"]), hide_index=True, width="stretch"
                )
            else:
                col.info("No data")

    with tabs[3]:
        tracking = r["context"]["supplier_tracking"]
        s1, s2, s3 = st.columns(3)
        s1.metric(
            "Traceability index",
            "–" if tracking["traceability_index"] is None else f"{tracking['traceability_index']:.0f} / 100",
        )
        s2.metric("Purchases from tracked suppliers", _pct(tracking["tracking_share"]))
        s3.metric("Purchases, last 12 months", f"{tracking['purchase_value_12m']:,.0f}")
        st.dataframe(
            pd.DataFrame([{"Tier": f"Tier {k}", "Suppliers": v} for k, v in tracking["tier_counts"].items()]),
            hide_index=True,
        )
        st.caption(
            "Tier 1: purchases recorded · Tier 2: + inventory linked to the supplier · "
            "Tier 3: + full chain (delivery, bill, payment) and sales of its items"
        )

    with tabs[4]:
        cov = pd.DataFrame(r["data_coverage"])
        cov["errors"] = cov["errors"].apply(lambda e: "; ".join(e))
        st.dataframe(cov, hide_index=True, width="stretch")
        st.dataframe(pd.DataFrame(r["record_counts"].items(), columns=["Table", "Records"]), hide_index=True)

    with tabs[5]:
        st.download_button(
            "Download result (JSON)",
            json.dumps(r, indent=2, default=str),
            file_name=f"health-score-{biz['company_code']}-{r['as_of']}.json",
            mime="application/json",
        )
        st.json(r, expanded=False)
