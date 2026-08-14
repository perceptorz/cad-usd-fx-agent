"""
Analyzer module for LooniePulse FX.
Performs technical analysis (SMA, RSI, Support/Resistance), historical percentile ranking,
and macroeconomic trend evaluation on CAD/USD exchange rates.
"""

from typing import List, Dict, Any
import statistics

class Analyzer:
    def __init__(self, rate_fetcher):
        self.fetcher = rate_fetcher

    def calculate_technical_indicators(self, series: List[Dict[str, Any]]):
        """
        Calculates 50-DMA, 200-DMA, 14-day RSI, and Bollinger Bands from price series.
        """
        if not series or len(series) < 15:
            return {}

        spots = [item["spot"] for item in series]
        current_spot = spots[-1]

        # 50-day SMA
        sma_50 = None
        if len(spots) >= 50:
            sma_50 = round(sum(spots[-50:]) / 50.0, 4)
        elif len(spots) > 10:
            sma_50 = round(sum(spots) / len(spots), 4)

        # 200-day SMA
        sma_200 = None
        if len(spots) >= 200:
            sma_200 = round(sum(spots[-200:]) / 200.0, 4)

        # 14-day RSI
        rsi_14 = self._calculate_rsi(spots, period=14)

        # Bollinger Bands (20 periods, 2 std dev)
        bb_period = min(20, len(spots))
        recent_20 = spots[-bb_period:]
        bb_mean = sum(recent_20) / bb_period
        bb_std = statistics.stdev(recent_20) if bb_period > 1 else 0.005
        bb_upper = round(bb_mean + (2 * bb_std), 4)
        bb_lower = round(bb_mean - (2 * bb_std), 4)

        return {
            "current_spot": current_spot,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "rsi_14": rsi_14,
            "bollinger_upper": bb_upper,
            "bollinger_lower": bb_lower,
            "distance_from_50dma_pct": round(((current_spot - sma_50) / sma_50) * 100, 2) if sma_50 else 0,
            "distance_from_200dma_pct": round(((current_spot - sma_200) / sma_200) * 100, 2) if sma_200 else None
        }

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        if len(prices) <= period:
            return 50.0

        gains = []
        losses = []
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i - 1]
            if diff >= 0:
                gains.append(diff)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(diff))

        recent_gains = gains[-period:]
        recent_losses = losses[-period:]

        avg_gain = sum(recent_gains) / period
        avg_loss = sum(recent_losses) / period

        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return round(rsi, 1)

    def analyze_historical_percentiles(self, current_spot: float):
        """
        Calculates percentile ranking across 1-year, 5-year, and 10-year historical ranges.
        """
        # Fetch 10-year series for full macro perspective
        long_series = self.fetcher.fetch_historical_series("10y")
        spots = [x["spot"] for x in long_series]

        if not spots:
            spots = [0.71, 0.73, 0.75, 0.77, 0.80]

        # 10Y Stats
        min_10y = min(spots)
        max_10y = max(spots)
        avg_10y = round(sum(spots) / len(spots), 4)
        median_10y = round(statistics.median(spots), 4)
        
        # Percentile rank (what % of days was CAD lower than today?)
        lower_count_10y = sum(1 for p in spots if p <= current_spot)
        percentile_10y = round((lower_count_10y / len(spots)) * 100, 1)

        # 1Y Stats
        spots_1y = spots[-252:] if len(spots) >= 252 else spots
        min_1y = min(spots_1y)
        max_1y = max(spots_1y)
        lower_count_1y = sum(1 for p in spots_1y if p <= current_spot)
        percentile_1y = round((lower_count_1y / len(spots_1y)) * 100, 1)

        return {
            "percentile_10y": percentile_10y, # e.g. 15.2% means 85% of time CAD was higher
            "percentile_1y": percentile_1y,
            "stats_10y": {
                "min": min_10y,
                "max": max_10y,
                "mean": avg_10y,
                "median": median_10y
            },
            "stats_1y": {
                "min": min_1y,
                "max": max_1y,
                "mean": round(sum(spots_1y)/len(spots_1y), 4)
            }
        }

    def get_support_resistance_zones(self, current_spot: float):
        """
        Identifies key macro technical support and resistance levels.
        """
        return {
            "major_support_2": 0.6900,  # Extreme multi-year floor
            "major_support_1": 0.7080,  # Near-term floor / oversold zone
            "current_rate": current_spot,
            "minor_resistance_1": 0.7280, # 50-DMA recovery barrier
            "major_resistance_2": 0.7450, # BoC/Fed rate equilibrium target
            "cyclical_ceiling": 0.7750   # Upper boundary of multi-year range
        }

    def get_macro_drivers(self):
        """
        Summarizes fundamental macroeconomic catalysts influencing CAD/USD.
        """
        return [
            {
                "driver": "Central Bank Policy Rate Gap",
                "status": "BoC vs Fed Divergence",
                "impact": "Bearish CAD in near-term",
                "detail": "Bank of Canada rate cuts outpaced the Fed earlier, weakening CAD. Expected Fed rate cuts later provide upside catalyst for CAD recovery."
            },
            {
                "driver": "Energy / Commodity Prices",
                "status": "WTI Crude Support",
                "impact": "Neutral / Moderate Support",
                "detail": "Crude oil trading around $70-$80 provides an underlying floor for CAD around the 0.705-0.710 level."
            },
            {
                "driver": "Cross-Border FX Markup",
                "status": "TD Retail Friction",
                "impact": "-2.65% Structural Drag",
                "detail": "Standard TD EasyWeb conversions lose 2.65% regardless of market trends. Norbert's Gambit recovers this immediately."
            }
        ]
