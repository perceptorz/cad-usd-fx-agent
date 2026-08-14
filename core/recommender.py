"""
Recommender module for LooniePulse FX.
Generates comprehensive transfer feasibility verdicts, target price ladders,
and quantitative cost/benefit breakdowns across TD channels and Norbert's Gambit.
"""

from typing import Dict, Any

class Recommender:
    def __init__(self, rate_fetcher, analyzer):
        self.fetcher = rate_fetcher
        self.analyzer = analyzer

    def generate_recommendation(self, transfer_amount_cad: float = 50000.0) -> Dict[str, Any]:
        """
        Generates full analysis and recommendations for transferring CAD to USD.
        """
        current_rates = self.fetcher.get_current_rates()
        spot = current_rates["spot_cadusd"]
        td_retail = current_rates["td_bank"]["retail_rate"]
        norbert_raw = current_rates["alternatives"]["norberts_gambit"]["effective_rate_raw"]

        # Historical series & technicals
        history_1y = self.fetcher.fetch_historical_series("1y")
        technicals = self.analyzer.calculate_technical_indicators(history_1y)
        percentiles = self.analyzer.analyze_historical_percentiles(spot)
        support_resistance = self.analyzer.get_support_resistance_zones(spot)
        macro_drivers = self.analyzer.get_macro_drivers()

        # Compute feasibility score (0 to 100)
        # Higher score = more attractive rate to transfer CAD to USD
        percentile_10y = percentiles.get("percentile_10y", 20.0)
        rsi = technicals.get("rsi_14", 45.0)
        
        # Base score driven by 10Y percentile rank (0% = 0 pts, 100% = 70 pts)
        base_score = percentile_10y * 0.70
        
        # RSI momentum bonus (overbought > 70 gives extra timing score for selling CAD)
        rsi_factor = (rsi / 100.0) * 30.0
        
        feasibility_score = round(base_score + rsi_factor, 1)

        # Determine Primary Action Verdict
        if feasibility_score < 40.0:
            verdict_badge = "UNFAVORABLE (HOLD)"
            verdict_summary = "CAD is currently near historical cycle lows (bottom 15-20% of 10-year range). Standard TD retail transfer converts at an unfavorable rate (~0.70-0.71)."
            action_advice = "HOLD standard transfer if time permits. Set rate alert for Target 1 (0.7300) or Target 2 (0.7450). If immediate transfer is required, use Norbert's Gambit on TD Direct Investing to bypass bank fees."
        elif feasibility_score < 70.0:
            verdict_badge = "NEUTRAL / RECOVERING"
            verdict_summary = "CAD is trading near fair medium-term value with moderate upside potential toward the 50-day and 200-day moving averages."
            action_advice = "Consider a staggered transfer (dollar-cost averaging) or execute via Norbert's Gambit to capture near-spot rates."
        else:
            verdict_badge = "HIGHLY FAVORABLE"
            verdict_summary = "CAD is trading in the upper percentile of its historical range. Excellent timing for converting CAD to USD."
            action_advice = "EXECUTE TRANSFER: Take advantage of strong CAD valuation."

        # Target Price Ladder
        target_ladder = [
            {
                "tier": "Current Spot Benchmark",
                "spot_rate": spot,
                "td_retail_rate": td_retail,
                "norbert_rate": norbert_raw,
                "probability": "Active Now",
                "usd_received_td": round(transfer_amount_cad * td_retail, 2),
                "usd_received_norbert": round(transfer_amount_cad * norbert_raw - (9.99 * 2 * spot), 2),
                "horizon": "Immediate"
            },
            {
                "tier": "Target 1: Near-Term Rebound (50-DMA)",
                "spot_rate": 0.7300,
                "td_retail_rate": round(0.7300 * (1 - 0.0265), 4),
                "norbert_rate": round(0.7300 * (1 - 0.0010), 4),
                "probability": "Moderate (~60% in 1-3 mos)",
                "usd_received_td": round(transfer_amount_cad * 0.7300 * (1 - 0.0265), 2),
                "usd_received_norbert": round(transfer_amount_cad * 0.7300 * (1 - 0.0010) - (9.99 * 2 * 0.73), 2),
                "horizon": "1 - 3 Months"
            },
            {
                "tier": "Target 2: Macro Balance (BoC/Fed Parity)",
                "spot_rate": 0.7450,
                "td_retail_rate": round(0.7450 * (1 - 0.0265), 4),
                "norbert_rate": round(0.7450 * (1 - 0.0010), 4),
                "probability": "Selective (~40% in 3-6 mos)",
                "usd_received_td": round(transfer_amount_cad * 0.7450 * (1 - 0.0265), 2),
                "usd_received_norbert": round(transfer_amount_cad * 0.7450 * (1 - 0.0010) - (9.99 * 2 * 0.745), 2),
                "horizon": "3 - 6 Months"
            },
            {
                "tier": "Target 3: Historical 10-Yr Median Reversion",
                "spot_rate": 0.7650,
                "td_retail_rate": round(0.7650 * (1 - 0.0265), 4),
                "norbert_rate": round(0.7650 * (1 - 0.0010), 4),
                "probability": "Optimistic (~25% in 6-12 mos)",
                "usd_received_td": round(transfer_amount_cad * 0.7650 * (1 - 0.0265), 2),
                "usd_received_norbert": round(transfer_amount_cad * 0.7650 * (1 - 0.0010) - (9.99 * 2 * 0.765), 2),
                "horizon": "6 - 12 Months"
            }
        ]

        # Channel Comparison for transfer_amount_cad
        usd_at_spot = transfer_amount_cad * spot
        usd_at_td_retail = transfer_amount_cad * td_retail
        usd_at_td_wire = transfer_amount_cad * current_rates["td_bank"]["wire_rate"] - 30.0 # $30 wire fee
        usd_at_wise = transfer_amount_cad * current_rates["alternatives"]["wise"]["rate"]
        
        # Norbert: CAD -> buy DLR.TO -> Journal to DLR.U.TO -> Sell for USD. Two $9.99 CAD trades
        norbert_commission_usd = (9.99 * 2) * spot
        usd_at_norbert = (transfer_amount_cad * norbert_raw) - norbert_commission_usd

        channel_comparison = [
            {
                "channel": "Norbert's Gambit (TD Direct Investing)",
                "effective_rate": round(usd_at_norbert / transfer_amount_cad, 5),
                "usd_received": round(usd_at_norbert, 2),
                "spread_cost_usd": round(usd_at_spot - usd_at_norbert, 2),
                "savings_vs_td_retail": round(usd_at_norbert - usd_at_td_retail, 2),
                "settlement_time": "1-2 Business Days",
                "is_recommended": True
            },
            {
                "channel": "Wise / Specialized FX Broker",
                "effective_rate": round(usd_at_wise / transfer_amount_cad, 5),
                "usd_received": round(usd_at_wise, 2),
                "spread_cost_usd": round(usd_at_spot - usd_at_wise, 2),
                "savings_vs_td_retail": round(usd_at_wise - usd_at_td_retail, 2),
                "settlement_time": "1-2 Business Days",
                "is_recommended": False
            },
            {
                "channel": "TD Bank Wire Transfer",
                "effective_rate": round(usd_at_td_wire / transfer_amount_cad, 5),
                "usd_received": round(usd_at_td_wire, 2),
                "spread_cost_usd": round(usd_at_spot - usd_at_td_wire, 2),
                "savings_vs_td_retail": round(usd_at_td_wire - usd_at_td_retail, 2),
                "settlement_time": "Same Day / Next Day",
                "is_recommended": False
            },
            {
                "channel": "TD EasyWeb Standard Retail FX",
                "effective_rate": round(usd_at_td_retail / transfer_amount_cad, 5),
                "usd_received": round(usd_at_td_retail, 2),
                "spread_cost_usd": round(usd_at_spot - usd_at_td_retail, 2),
                "savings_vs_td_retail": 0.0,
                "settlement_time": "Instant",
                "is_recommended": False
            }
        ]

        return {
            "transfer_amount_cad": transfer_amount_cad,
            "feasibility_score": feasibility_score, # 0-100
            "verdict_badge": verdict_badge,
            "verdict_summary": verdict_summary,
            "action_advice": action_advice,
            "current_rates": current_rates,
            "technicals": technicals,
            "percentiles": percentiles,
            "support_resistance": support_resistance,
            "macro_drivers": macro_drivers,
            "target_ladder": target_ladder,
            "channel_comparison": channel_comparison,
            "key_takeaway": f"Converting ${transfer_amount_cad:,.0f} CAD directly via TD EasyWeb loses ~${(usd_at_spot - usd_at_td_retail):,.2f} USD to the bank spread. Using Norbert's Gambit saves ~${(usd_at_norbert - usd_at_td_retail):,.2f} USD immediately, regardless of when you transfer."
        }
