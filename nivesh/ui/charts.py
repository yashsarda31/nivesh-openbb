"""Shared Plotly chart factories that retain exact source values."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import plotly.graph_objects as go

from nivesh.domain.models import FinancialPeriod, PricePoint

GRAPHITE = "#202124"
MUTED = "#667085"
GRID = "rgba(32, 33, 36, 0.10)"
SERIES_COLORS = ("#0A7B66", "#2878FF", "#8A5CF6", "#D97706")

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
    figure = go.Figure(
        go.Scatter(
            x=[point.date for point in ordered],
            y=[point.close for point in ordered],
            name=symbol,
            mode="lines",
            line={"color": SERIES_COLORS[0], "width": 2.5},
            connectgaps=False,
            customdata=[[point.volume] for point in ordered],
            hovertemplate=(
                "%{x|%d %b %Y}<br>Close %{y:,.2f}<br>Volume %{customdata[0]:,.0f}"
                "<extra>%{fullData.name}</extra>"
            ),
        )
    )
    return _apply_layout(figure, y_title="Close price", show_legend=False)


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
        height=360,
        margin={"l": 16, "r": 16, "t": 20, "b": 16},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": GRAPHITE, "family": "Inter, Arial, sans-serif", "size": 12},
        hovermode="x unified",
        showlegend=show_legend,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        yaxis_title=y_title,
        hoverlabel={"bgcolor": "white", "font_color": GRAPHITE},
    )
    figure.update_xaxes(showgrid=False, zeroline=False)
    figure.update_yaxes(gridcolor=GRID, zeroline=False)
    return figure
