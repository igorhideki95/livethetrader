from __future__ import annotations

import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from livethetrader.ui.dashboard_client import DashboardClient
from livethetrader.ui.models import DashboardSnapshot

st.set_page_config(page_title="LiveTheTrader Dashboard", layout="wide")


@st.cache_resource
def get_client() -> DashboardClient:
    base_url = os.getenv("DASHBOARD_API_URL", "http://localhost:8000")
    timeout = float(os.getenv("DASHBOARD_API_TIMEOUT", "5"))
    return DashboardClient(base_url=base_url, timeout=timeout)


def plot_candles(snapshot: DashboardSnapshot) -> go.Figure:
    frame = pd.DataFrame(
        [
            {
                "time": c.time,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "signal": c.signal,
                **(c.indicators or {}),
            }
            for c in snapshot.candles
        ]
    )

    fig = go.Figure()
    if frame.empty:
        fig.update_layout(title="Sem candles disponíveis.")
        return fig

    fig.add_trace(
        go.Candlestick(
            x=frame["time"],
            open=frame["open"],
            high=frame["high"],
            low=frame["low"],
            close=frame["close"],
            name="Candles",
        )
    )

    base_cols = {"time", "open", "high", "low", "close", "signal"}
    for indicator in [col for col in frame.columns if col not in base_cols]:
        fig.add_trace(
            go.Scatter(
                x=frame["time"],
                y=frame[indicator],
                mode="lines",
                name=indicator,
            )
        )

    buy = frame[frame["signal"] == "CALL"]
    sell = frame[frame["signal"] == "PUT"]

    if not buy.empty:
        fig.add_trace(
            go.Scatter(
                x=buy["time"],
                y=buy["close"],
                mode="markers",
                marker=dict(symbol="triangle-up", size=10),
                name="Sinal CALL",
            )
        )
    if not sell.empty:
        fig.add_trace(
            go.Scatter(
                x=sell["time"],
                y=sell["close"],
                mode="markers",
                marker=dict(symbol="triangle-down", size=10),
                name="Sinal PUT",
            )
        )

    fig.update_layout(
        title="Candles + Indicadores + Marcações",
        xaxis_title="Horário",
        yaxis_title="Preço",
        xaxis_rangeslider_visible=False,
        legend_orientation="h",
    )
    return fig


def plot_equity_curve(snapshot: DashboardSnapshot) -> go.Figure:
    points = snapshot.metrics.equity_curve or []
    frame = pd.DataFrame([{"time": p.time, "equity": p.equity} for p in points])
    fig = go.Figure()

    if frame.empty:
        fig.update_layout(title="Sem curva de capital disponível.")
        return fig

    fig.add_trace(
        go.Scatter(x=frame["time"], y=frame["equity"], mode="lines", name="Curva de capital")
    )
    fig.update_layout(title="Curva de capital", xaxis_title="Horário", yaxis_title="Capital")
    return fig


def render_controls(client: DashboardClient) -> None:
    st.subheader("Controles operacionais")
    col1, col2, col3, col4 = st.columns(4)

    controls = [
        (col1, "Iniciar", "start"),
        (col2, "Pausar", "pause"),
        (col3, "Reiniciar", "restart"),
        (col4, "Recarregar config", "reload-config"),
    ]

    for column, label, action in controls:
        with column:
            if st.button(label, use_container_width=True):
                ok, message = client.send_control(action)
                if ok:
                    st.success(message)
                else:
                    st.error(message)


def render_history(snapshot: DashboardSnapshot) -> None:
    st.subheader("Histórico de trades")
    history = pd.DataFrame(
        [
            {
                "time": h.time,
                "symbol": h.symbol,
                "signal": h.signal,
                "confidence": h.confidence,
                "result": h.result,
                "pnl": h.pnl,
            }
            for h in snapshot.history
        ]
    )

    if history.empty:
        st.info("Sem histórico disponível.")
        return

    symbols = sorted(history["symbol"].dropna().unique().tolist())
    selected_symbols = st.multiselect("Filtro por símbolo", symbols, default=symbols)
    if selected_symbols:
        history = history[history["symbol"].isin(selected_symbols)]

    results = sorted(history["result"].dropna().unique().tolist())
    selected_results = st.multiselect("Filtro por resultado", results, default=results)
    if selected_results:
        history = history[history["result"].isin(selected_results)]

    sort_by = st.selectbox("Ordenar por", ["time", "pnl", "confidence"], index=0)
    descending = st.checkbox("Ordem decrescente", value=True)
    history = history.sort_values(by=sort_by, ascending=not descending)

    st.dataframe(history, use_container_width=True, hide_index=True)


def main() -> None:
    st.title("LiveTheTrader Dashboard")
    st.caption(
        "UI desacoplada do backend. Dados carregados de /api/v1/dashboard via polling HTTP."
    )

    refresh_seconds = st.sidebar.slider("Atualização automática (segundos)", 1, 30, 3)
    st.sidebar.write("Defina DASHBOARD_API_URL para apontar para outro backend.")

    client = get_client()
    try:
        snapshot = client.get_snapshot()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    status_col, signal_col, confidence_col, time_col = st.columns(4)
    status_col.metric("Status", snapshot.status)
    signal_col.metric("Sinal atual", snapshot.current_signal.direction)
    confidence_col.metric("Confiança", f"{snapshot.current_signal.confidence:.2%}")
    time_col.metric("Horário", snapshot.current_signal.timestamp or snapshot.updated_at)

    render_controls(client)

    chart_col, equity_col = st.columns([2, 1])
    with chart_col:
        st.plotly_chart(plot_candles(snapshot), use_container_width=True)
    with equity_col:
        st.subheader("Performance")
        st.metric("Win rate", f"{snapshot.metrics.win_rate:.2%}")
        st.metric("Profit factor", f"{snapshot.metrics.profit_factor:.2f}")
        st.metric("Drawdown", f"{snapshot.metrics.drawdown:.2f}")
        st.metric("Trades", str(snapshot.metrics.trades))
        st.metric("Expectativa", f"{snapshot.metrics.expectancy:.4f}")

    st.plotly_chart(plot_equity_curve(snapshot), use_container_width=True)
    render_history(snapshot)

    st.autorefresh(interval=refresh_seconds * 1000, key="dashboard-refresh")


if __name__ == "__main__":
    main()
