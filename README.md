# LooniePulse FX: Autonomous CAD/USD Rate Tracker & Recommendation Agent for TD Bank

LooniePulse FX is a financial intelligence agent and interactive control center designed to optimize cross-border CAD to USD transfers from Canadian banks (specifically **TD Canada Trust**) to the United States.

## Key Capabilities

1. **Interbank vs. TD Retail Rate Tracking**: Tracks live CAD/USD spot benchmarks (Bank of Canada Valet API & Yahoo Finance) against TD Bank's retail spreads (~2.65% margin), wire rates, and Norbert's Gambit execution.
2. **Historical Trend & Valuation Analytics**: Computes 1Y, 5Y, and 10Y rolling percentiles, 50-DMA / 200-DMA moving averages, 14-day RSI momentum, and macro rate differentials (BoC vs Fed).
3. **Actionable Transfer Feasibility Verdict**: Clarifies why rates around ~0.71 sit in the bottom ~15th percentile of historical cycles, recommends target ladders (0.7300, 0.7450, 0.7650), and calculates exact dollar gains from **Norbert's Gambit** on TD Direct Investing.
4. **Autonomous Notification Engine**: Configurable trigger watcher with multi-channel dispatch:
   - Native macOS Desktop Notifications (`osascript`)
   - Webhooks (Discord, Slack, custom endpoints)
   - In-app logs and audio chimes
5. **Interactive Web Control Center & CLI**: Modern web dashboard with Chart.js visualization, real-time transfer calculator, alert manager, and simulator.

---

## Quick Start

### 1. Check Current Status & Recommendations via CLI
```bash
# Quick status check
python3 agent.py --status

# In-depth transfer recommendation for $50,000 CAD
python3 agent.py --recommend --amount 50000
```

### 2. Start the Interactive Web Dashboard
```bash
python3 agent.py --serve --port 8080
# Or: python3 server.py
```
Open **http://localhost:8080** in your browser.

### 3. Run the Autonomous Monitoring Daemon
```bash
# Monitor rates in background, polling every 60 seconds with target alert at 0.7350
python3 agent.py --monitor --target 0.7350 --interval 60
```

### 4. Test macOS Desktop Notifications
```bash
python3 agent.py --test-notify
```

---

## File Structure

```
cad-usd-fx-agent/
├── agent.py                 # Main CLI agent & autonomous daemon
├── server.py                # REST API & static web server
├── core/
│   ├── __init__.py
│   ├── database.py          # SQLite persistence for rate ticks, alerts, and logs
│   ├── rate_fetcher.py      # BoC Valet API, Yahoo Finance, & TD spread calculation
│   ├── analyzer.py          # Technical indicators, 10Y percentiles, macro drivers
│   ├── recommender.py       # Feasibility verdicts, target ladder, Norbert's model
│   └── notifier.py          # macOS desktop notification & webhook dispatch
├── static/
│   ├── index.html           # Interactive dashboard & control center
│   ├── app.css              # Obsidian slate financial theme (responsive CSS)
│   └── app.js               # Reactive frontend logic & Chart.js integration
└── README.md
```
