"""Shared Plotly chart factories that retain exact source values."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import plotly.graph_objects as go

from nivesh.domain.models import FinancialPeriod, PricePoint

GRAPHITE = "#0F1B2D"
MUTED = "#5B6B82"
GRID = "rgba(15, 27, 45, 0.07)"
SERIES_COLORS = ("#087F70", "#4F46E5", "#0EA5E9", "#D97706")
UP = "#0A8F6A"
DOWN = "#D43F5E"

METRIC_LABELS = {
    "revenue": "Revenue",
    "operating_income": "Operating profit",
    "ebitda": "EBITDA",
    "net_income": "Net income",
    "diluted_eps": "Diluted EPS",
    "operating_cash_flow": "Operating cash flow",
    "capital_expenditure": "Capital expenditure",
    "free_cash_flow": "Free cash flow",
    "operating_margin": "Operating margin",
    "net_margin": "Net margin",
    "roe": "Return on equity",
    "roa": "Return on assets",
}


def empty_figure(message: str = "Data unavailable for the selected view.") -> go.Figure:
    """Return a styled, explanatory empty state instead of a blank chart."""

    figure = go.Figure()
    figure.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"color": MUTED, "size": 14},
    )
    return _apply_layout(figure, show_legend=False)


def financial_trend_figure(
    periods: Sequence[FinancialPeriod], metrics: Sequence[str]
) -> go.Figure:
    """Plot reported financial values across aligned statement periods."""

    if not periods or not metrics:
        return empty_figure("Financial history is unavailable for this selection.")

    ordered = sorted(periods, key=lambda period: period.period_ending)
    figure = go.Figure()
    for index, metric in enumerate(metrics):
        values = [getattr(period, metric, None) for period in ordered]
        figure.add_trace(
            go.Bar(
                x=[period.period_ending for period in ordered],
                y=values,
                name=METRIC_LABELS.get(metric, metric.replace("_", " ").title()),
                marker_color=SERIES_COLORS[index % len(SERIES_COLORS)],
                hovertemplate="%{y:,.2f}<extra>%{fullData.name}</extra>",
            )
        )
    figure = _apply_layout(figure, y_title="Reported value")
    figure.update_layout(barmode="group")
    return figure


def margin_figure(
    periods: Sequence[FinancialPeriod], metrics: Sequence[str]
) -> go.Figure:
    """Plot profitability ratios while retaining their decimal source values."""

    if not periods or not metrics:
        return empty_figure("Margin history is unavailable for this selection.")

    ordered = sorted(periods, key=lambda period: period.period_ending)
    figure = go.Figure()
    for index, metric in enumerate(metrics):
        figure.add_trace(
            go.Bar(
                x=[period.period_ending for period in ordered],
                y=[period.metrics.get(metric) for period in ordered],
                name=METRIC_LABELS.get(metric, metric.replace("_", " ").title()),
                marker_color=SERIES_COLORS[index % len(SERIES_COLORS)],
                hovertemplate="%{y:.2%}<extra>%{fullData.name}</extra>",
            )
        )
    figure = _apply_layout(figure, y_title="Margin")
    figure.update_yaxes(tickformat=".0%")
    figure.update_layout(barmode="group")
    return figure


def price_figure(points: Sequence[PricePoint], *, symbol: str) -> go.Figure:
    """Plot exact historical closes for one listed company."""

    if not points:
        return empty_figure("Price history is unavailable from the selected provider.")

    ordered = sorted(points, key=lambda point: point.date)
    closes = [point.close for point in ordered]
    color = DOWN if len(closes) > 1 and closes[-1] < closes[0] else UP
    rgb = ",".join(str(int(color[index : index + 2], 16)) for index in (1, 3, 5))
    low, high = min(closes), max(closes)
    padding = (high - low) * 0.08 or high * 0.02 or 1.0
    figure = go.Figure(
        go.Scatter(
            x=[point.date for point in ordered],
            y=closes,
            name=symbol,
            mode="lines",
            line={"color": color, "width": 2.2, "shape": "linear"},
            # The fill is drawn to zero but the axis range clips it, so the
            # gradient never implies a zero-based scale.
            fill="tozeroy",
            fillgradient={
                "type": "vertical",
                "colorscale": [[0, f"rgba({rgb},0)"], [1, f"rgba({rgb},0.22)"]],
            },
            connectgaps=False,
            customdata=[[point.volume] for point in ordered],
            hovertemplate=(
                "%{x|%d %b %Y}<br><b>%{y:,.2f}</b> close<br>Volume %{customdata[0]:,.0f}"
                "<extra></extra>"
            ),
        )
    )
    figure = _apply_layout(figure, y_title=None, show_legend=False)
    figure.update_yaxes(range=[low - padding, high + padding], side="right")
    return figure


def comparison_figure(frame: pd.DataFrame, *, y_title: str) -> go.Figure:
    """Plot aligned comparison series without filling missing observations."""

    if frame.empty or frame.columns.empty:
        return empty_figure("Comparison data is unavailable for this selection.")

    figure = go.Figure()
    for index, column in enumerate(frame.columns):
        figure.add_trace(
            go.Scatter(
                x=frame.index,
                y=frame[column].tolist(),
                name=str(column),
                mode="lines",
                line={"color": SERIES_COLORS[index % len(SERIES_COLORS)], "width": 2.5},
                connectgaps=False,
                hovertemplate="%{y:,.2f}<extra>%{fullData.name}</extra>",
            )
        )
    return _apply_layout(figure, y_title=y_title)


def _apply_layout(
    figure: go.Figure,
    *,
    y_title: str | None = None,
    show_legend: bool = True,
) -> go.Figure:
    figure.update_layout(
        height=340,
        margin={"l": 8, "r": 8, "t": 28 if show_legend else 12, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": MUTED, "family": "Inter, Arial, sans-serif", "size": 11.5},
        hovermode="x unified",
        showlegend=show_legend,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "x": 0,
            "font": {"color": GRAPHITE, "size": 12},
            "itemsizing": "constant",
        },
        yaxis_title=y_title,
        hoverlabel={
            "bgcolor": "white",
            "bordercolor": "#E3E8F0",
            "font": {"color": GRAPHITE, "family": "Inter, Arial, sans-serif", "size": 12},
        },
        barcornerradius=4,
        bargap=0.28,
        bargroupgap=0.08,
    )
    figure.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=True,
        linecolor="#E3E8F0",
        ticks="",
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikethickness=1,
        spikedash="dot",
        spikecolor="#94A3B8",
    )
    figure.update_yaxes(
        gridcolor=GRID,
        zeroline=False,
        ticks="",
        title_font={"size": 11.5, "color": MUTED},
    )
    return figure
