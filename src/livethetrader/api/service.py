from __future__ import annotations

from collections import defaultdict

from livethetrader.indicators.service import IndicatorService
from livethetrader.ingestion.mock_source import MockTickSource
from livethetrader.market_data.aggregator import MultiTimeframeCandleBuilder
from livethetrader.signal_engine.engine import SignalEngine


class TradingSignalService:
    """Facade that returns CALL|PUT|NEUTRO + confidence + expiry."""

    def __init__(self, symbol: str = "EURUSD") -> None:
        self.symbol = symbol
        self.source = MockTickSource(symbol=symbol)
        self.builder = MultiTimeframeCandleBuilder(symbol=symbol)
        self.indicators = IndicatorService()
        self.engine = SignalEngine()

    def run_once(self, tick_count: int = 54000) -> dict:
        features_by_tf: dict[str, dict[str, float]] = defaultdict(dict)
        for tick in self.source.stream(count=tick_count):
            closed_candles = self.builder.update(tick)
            for candle in closed_candles:
                features = self.indicators.push(candle)
                if features:
                    features_by_tf[candle.timeframe] = features

        signal = self.engine.generate(symbol=self.symbol, features_by_tf=features_by_tf)
        return signal.to_contract()
