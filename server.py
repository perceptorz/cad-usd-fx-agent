"""
Server module for LooniePulse FX.
Provides high-performance REST API and static asset hosting for the web dashboard.
"""

import sys
import os
import json
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
sys.path.insert(0, BASE_DIR)

from core import (
    init_db,
    log_rate,
    get_recent_history,
    get_alerts,
    add_alert,
    delete_alert,
    toggle_alert,
    get_notification_logs,
    RateFetcher,
    Analyzer,
    Recommender,
    Notifier
)

fetcher = RateFetcher()
analyzer = Analyzer(fetcher)
recommender = Recommender(fetcher, analyzer)
notifier = Notifier()

class FXRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/rates/current":
            rates = fetcher.get_current_rates()
            # Log snapshot to DB
            log_rate(
                rates["spot_cadusd"],
                rates["td_bank"]["retail_rate"],
                rates["td_bank"]["spread_pct"],
                rates["alternatives"]["norberts_gambit"]["effective_rate_raw"]
            )
            # Evaluate alerts in background
            notifier.check_and_trigger_alerts(rates["spot_cadusd"], rates["td_bank"]["retail_rate"])
            self._send_json(rates)

        elif path == "/api/rates/history":
            period = query.get("period", ["1y"])[0]
            history = fetcher.fetch_historical_series(period)
            self._send_json({"period": period, "count": len(history), "history": history})

        elif path == "/api/recommendation":
            amount = float(query.get("amount", [50000.0])[0])
            rec = recommender.generate_recommendation(amount)
            self._send_json(rec)

        elif path == "/api/alerts":
            alerts = get_alerts()
            logs = get_notification_logs(15)
            self._send_json({"alerts": alerts, "logs": logs})

        elif path == "/api/recent-snapshots":
            snapshots = get_recent_history(50)
            self._send_json(snapshots)

        else:
            # Fallback to static files
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if path == "/api/alerts":
            target_rate = float(payload.get("target_rate", 0.7350))
            comparison = payload.get("comparison", ">=")
            target_type = payload.get("target_type", "spot")
            channel = payload.get("channel", "all")
            webhook_url = payload.get("webhook_url", None)
            alert_id = add_alert(target_rate, comparison, target_type, channel, webhook_url)
            self._send_json({"success": True, "alert_id": alert_id})

        elif path == "/api/alerts/toggle":
            alert_id = int(payload.get("id"))
            is_active = bool(payload.get("is_active"))
            toggle_alert(alert_id, is_active)
            self._send_json({"success": True})

        elif path == "/api/alerts/delete":
            alert_id = int(payload.get("id"))
            delete_alert(alert_id)
            self._send_json({"success": True})

        elif path == "/api/alerts/test":
            notifier.send_notification(
                title="LooniePulse FX Desktop Alert 🎯",
                message="Your notification engine is actively monitoring CAD/USD for TD Bank transfers!",
                channel="all",
                rate_val=0.7350
            )
            self._send_json({"success": True, "message": "Test notification dispatched to macOS Notification Center"})

        elif path == "/api/simulate-rate":
            # Allows user in UI to test what happens when rate spikes to user-specified level
            sim_spot = float(payload.get("spot_rate", 0.7350))
            sim_td = round(sim_spot * (1 - 0.0265), 4)
            triggered = notifier.check_and_trigger_alerts(sim_spot, sim_td)
            self._send_json({
                "simulated_spot": sim_spot,
                "simulated_td": sim_td,
                "triggered_alerts": triggered
            })

        else:
            self.send_error(404, "Endpoint not found")

def start_server(port=8080):
    init_db()
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, FXRequestHandler)
    print(f"\n🚀 LooniePulse FX Web Control Center running at: http://localhost:{port}")
    print(f"📊 Serving dashboard from: {STATIC_DIR}")
    print("Press Ctrl+C to terminate the server.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server.")
        httpd.server_close()

if __name__ == "__main__":
    start_server(8080)
