#!/usr/bin/env python3
"""
LooniePulse FX - Autonomous CAD to USD Exchange Rate Tracker & Recommendation Agent
Command-Line Interface and Daemon Runner.
"""

import sys
import os
import time
import argparse
from datetime import datetime

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core import (
    init_db,
    log_rate,
    get_alerts,
    add_alert,
    delete_alert,
    get_notification_logs,
    RateFetcher,
    Analyzer,
    Recommender,
    Notifier
)

def print_banner():
    print(r"""
========================================================================
   🇨🇦 ➡️ 🇺🇸  LooniePulse FX - TD CAD to USD Intelligence Agent
========================================================================
    """)

def run_status():
    fetcher = RateFetcher()
    analyzer = Analyzer(fetcher)
    recommender = Recommender(fetcher, analyzer)

    rates = fetcher.get_current_rates()
    rec = recommender.generate_recommendation(50000)

    spot = rates["spot_cadusd"]
    td_retail = rates["td_bank"]["retail_rate"]
    spread_pct = rates["td_bank"]["spread_pct"]
    norbert = rates["alternatives"]["norberts_gambit"]["effective_rate_raw"]

    print_banner()
    print(f"🕒 Timestamp:        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Interbank Spot:   1 CAD = ${spot:.4f} USD  (USD/CAD: {rates['spot_usdcad']:.4f})")
    print(f"🏦 TD Retail Rate:   1 CAD = ${td_retail:.4f} USD  [Spread: -{spread_pct:.2f}%]")
    print(f"⚡ Norbert's Gambit: 1 CAD = ${norbert:.4f} USD  [Spread: -0.10%]")
    print("-" * 72)
    print(f"🎯 Feasibility Verdict: {rec['verdict_badge']} (Score: {rec['feasibility_score']}/100)")
    print(f"💡 Strategy:            {rec['action_advice']}")
    print(f"💰 Insight for $50k CAD:")
    print(f"   • TD EasyWeb Payout:    ${50000 * td_retail:,.2f} USD")
    print(f"   • Norbert's Gambit:     ${(50000 * norbert) - (19.98 * spot):,.2f} USD  (+${((50000 * norbert) - (19.98 * spot)) - (50000 * td_retail):,.2f} USD more!)")
    print("=" * 72)

def run_recommend(amount_cad=50000.0):
    fetcher = RateFetcher()
    analyzer = Analyzer(fetcher)
    recommender = Recommender(fetcher, analyzer)

    rec = recommender.generate_recommendation(amount_cad)

    print_banner()
    print(f"💼 TRANSFER ANALYSIS FOR: ${amount_cad:,.2f} CAD")
    print(f"🎯 Feasibility Score:     {rec['feasibility_score']} / 100 ({rec['verdict_badge']})")
    print(f"📌 Market Summary:        {rec['verdict_summary']}")
    print(f"⚡ Actionable Advice:     {rec['action_advice']}")
    print("\n" + "=" * 72)
    print("📈 TARGET PRICE LADDER & HORIZONS")
    print("=" * 72)
    print(f"{'Target Tier':<30} | {'Spot':<7} | {'TD Retail':<9} | {'USD Recv (TD)':<14} | {'Horizon':<12}")
    print("-" * 72)
    for target in rec["target_ladder"]:
        print(f"{target['tier']:<30} | {target['spot_rate']:<7.4f} | {target['td_retail_rate']:<9.4f} | ${target['usd_received_td']:<13,.2f} | {target['horizon']:<12}")

    print("\n" + "=" * 72)
    print("🏦 TRANSFER CHANNEL COMPARISON (Where does your money go?)")
    print("=" * 72)
    print(f"{'Channel':<35} | {'Rate':<7} | {'USD Received':<14} | {'Net Savings vs TD'}")
    print("-" * 72)
    for ch in rec["channel_comparison"]:
        rec_flag = " ⭐ [RECOMMENDED]" if ch["is_recommended"] else ""
        print(f"{ch['channel'] + rec_flag:<35} | {ch['effective_rate']:<7.4f} | ${ch['usd_received']:<13,.2f} | +${ch['savings_vs_td_retail']:,.2f} USD")

    print("-" * 72)
    print(f"💡 KEY TAKEAWAY: {rec['key_takeaway']}")
    print("=" * 72)

def run_monitor(interval_sec=60, custom_target=None):
    print_banner()
    init_db()
    fetcher = RateFetcher()
    notifier = Notifier()

    if custom_target:
        add_alert(target_rate=custom_target, comparison=">=", target_type="spot", channel="all")
        print(f"🎯 Custom target alert set: CAD/USD Spot >= {custom_target:.4f}")

    print(f"🚀 Starting Autonomous Rate Watcher (Polling every {interval_sec}s)...")
    print("Press Ctrl+C to stop monitoring.\n")

    try:
        while True:
            rates = fetcher.get_current_rates()
            spot = rates["spot_cadusd"]
            td_retail = rates["td_bank"]["retail_rate"]
            norbert = rates["alternatives"]["norberts_gambit"]["effective_rate_raw"]

            # Log to DB
            log_rate(spot, td_retail, rates["td_bank"]["spread_pct"], norbert)

            # Check alerts
            triggered = notifier.check_and_trigger_alerts(spot, td_retail)

            now_str = datetime.now().strftime("%H:%M:%S")
            trigger_msg = f" 🚨 TRIGGERED {len(triggered)} ALERT(S)!" if triggered else ""
            print(f"[{now_str}] Spot: {spot:.4f} | TD Retail: {td_retail:.4f} | Norbert: {norbert:.4f}{trigger_msg}")

            time.sleep(interval_sec)
    except KeyboardInterrupt:
        print("\n🛑 Watcher stopped by user.")

def list_alerts():
    print_banner()
    alerts = get_alerts()
    print("📋 CONFIGURED ALERT RULES:")
    print("-" * 72)
    print(f"{'ID':<4} | {'Target Rate':<12} | {'Condition':<10} | {'Type':<10} | {'Channel':<8} | {'Active'}")
    print("-" * 72)
    for a in alerts:
        active_str = "✅ YES" if a["is_active"] else "❌ NO (Triggered)"
        print(f"{a['id']:<4} | {a['target_rate']:<12.4f} | {a['comparison']:<10} | {a['target_type']:<10} | {a['channel']:<8} | {active_str}")
    print("=" * 72)

def test_notification():
    notifier = Notifier()
    print("🔔 Dispatching test notification to macOS Notification Center...")
    res = notifier.send_notification(
        title="LooniePulse FX Test Alert 🎯",
        message="Your CAD/USD Rate Tracker is active and successfully connected to macOS Notification Center!",
        channel="all",
        rate_val=0.7350
    )
    if res:
        print("✅ Notification successfully sent!")

def run_daily_digest():
    fetcher = RateFetcher()
    analyzer = Analyzer(fetcher)
    recommender = Recommender(fetcher, analyzer)
    notifier = Notifier()

    rates = fetcher.get_current_rates()
    rec = recommender.generate_recommendation(50000)

    spot = rates["spot_cadusd"]
    usdcad = rates["spot_usdcad"]
    td_retail = rates["td_bank"]["retail_rate"]
    change_pct = rates.get("change_pct", 0.0)
    change_usd = rates.get("change_usd", 0.0)
    trend_sign = "+" if change_pct > 0 else ""
    trend_str = f"{trend_sign}{change_pct:.2f}% ({trend_sign}{change_usd:.4f} USD)"

    title = f"☀️ CAD/USD Morning Briefing • {spot:.4f} USD"
    msg = (
        f"Daily Trend: {trend_str} (USD/CAD: {usdcad:.4f})\n"
        f"• TD Retail: ${td_retail:.4f} | Spot: ${spot:.4f}\n"
        f"• Verdict: {rec['verdict_badge']} (10Y Percentile: {rec['percentiles']['percentile_10y']}%)\n"
        f"• Strategy: {rec['action_advice']}"
    )

    print_banner()
    print(f"☀️ DAILY MORNING RATE BRIEFING:")
    print(f"📊 Live Spot:      1 CAD = ${spot:.4f} USD  [{trend_str}]")
    print(f"🏦 TD Retail Rate: 1 CAD = ${td_retail:.4f} USD  [-2.65% spread]")
    print(f"⚡ Norbert's:      1 CAD = ${rates['alternatives']['norberts_gambit']['effective_rate_raw']:.4f} USD")
    print(f"🎯 10-Yr Position: {rec['percentiles']['percentile_10y']}% ({rec['verdict_badge']})")
    print(f"💡 Strategy:       {rec['action_advice']}")

    notifier.send_notification(title, msg, channel="all", rate_val=spot)

def main():
    parser = argparse.ArgumentParser(description="LooniePulse FX - TD CAD to USD Rate Tracker & Recommendation Agent")
    parser.add_argument("--status", action="store_true", help="Display current rates and quick status")
    parser.add_argument("--recommend", action="store_true", help="Display detailed transfer recommendations and channel comparison")
    parser.add_argument("--daily-digest", action="store_true", help="Run daily morning rate digest and send notification")
    parser.add_argument("--amount", type=float, default=50000.0, help="CAD transfer amount for calculations (default: $50,000)")
    parser.add_argument("--monitor", action="store_true", help="Run the autonomous rate monitoring loop")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds for monitor (default: 60)")
    parser.add_argument("--target", type=float, help="Set target rate threshold for monitor (e.g. 0.735)")
    parser.add_argument("--alerts", action="store_true", help="List all configured alert rules")
    parser.add_argument("--alert-add", type=float, help="Add a new target rate alert (e.g. --alert-add 0.74)")
    parser.add_argument("--alert-type", choices=["spot", "td_retail"], default="spot", help="Alert target type (default: spot)")
    parser.add_argument("--test-notify", action="store_true", help="Send a test notification")
    parser.add_argument("--serve", action="store_true", help="Launch interactive web dashboard")
    parser.add_argument("--port", type=int, default=8080, help="Web server port (default: 8080)")

    args = parser.parse_args()

    init_db()

    if args.status:
        run_status()
    elif args.recommend:
        run_recommend(args.amount)
    elif args.daily_digest:
        run_daily_digest()
    elif args.monitor:
        run_monitor(args.interval, args.target)
    elif args.alerts:
        list_alerts()
    elif args.alert_add:
        alert_id = add_alert(args.alert_add, ">=", args.alert_type, "all")
        print(f"✅ Added alert #{alert_id}: {args.alert_type.upper()} >= {args.alert_add:.4f}")
    elif args.test_notify:
        test_notification()
    elif args.serve:
        from server import start_server
        start_server(args.port)
    else:
        run_status()

if __name__ == "__main__":
    main()
