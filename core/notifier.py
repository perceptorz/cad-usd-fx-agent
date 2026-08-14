"""
Notifier module for LooniePulse FX.
Handles macOS native notifications (osascript), webhooks, and database logging.
"""

import os
import subprocess
import urllib.request
import json
from datetime import datetime
from .database import get_alerts, toggle_alert, log_notification, get_db_connection

class Notifier:
    def __init__(self):
        pass

    def send_macos_notification(self, title: str, message: str, subtitle: str = "LooniePulse FX"):
        """
        Sends a native macOS notification using AppleScript (osascript).
        """
        try:
            # Escape double quotes
            safe_title = title.replace('"', '\\"')
            safe_message = message.replace('"', '\\"')
            safe_subtitle = subtitle.replace('"', '\\"')
            
            script = f'display notification "{safe_message}" with title "{safe_title}" subtitle "{safe_subtitle}" sound name "Glass"'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)
            return True
        except Exception as e:
            print(f"[Notifier] macOS notification error: {e}")
            return False

    def send_webhook(self, webhook_url: str, title: str, message: str, rate_val: float):
        """
        Dispatches payload to a Discord/Slack or custom webhook URL.
        """
        if not webhook_url:
            return False
        try:
            payload = {
                "username": "LooniePulse FX Agent",
                "content": f"🚨 **{title}**\n{message}\n*Triggered Rate: {rate_val:.4f}*",
                "embeds": [{
                    "title": title,
                    "description": message,
                    "color": 3066993, # Emerald green
                    "fields": [
                        {"name": "Trigger Rate", "value": f"{rate_val:.4f}", "inline": True},
                        {"name": "Timestamp", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": True}
                    ]
                }]
            }
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={'Content-Type': 'application/json', 'User-Agent': 'LooniePulse-FX-Agent'}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status in (200, 204)
        except Exception as e:
            print(f"[Notifier] Webhook dispatch error: {e}")
            return False

    def send_notification(self, title: str, message: str, channel: str = "all", rate_val: float = 0.0, webhook_url: str = None):
        """
        Broadcasts notification across requested channels and records in database log.
        """
        print(f"\n[🔔 NOTIFICATION DISPATCH] {title}: {message}")
        
        # 1. Native macOS Notification
        if channel in ("all", "system"):
            self.send_macos_notification(title, message)

        # 2. Webhook
        if channel in ("all", "webhook") and webhook_url:
            self.send_webhook(webhook_url, title, message, rate_val)

        # 3. Log in DB
        log_notification(title, message, channel, rate_val)
        return True

    def check_and_trigger_alerts(self, current_spot: float, td_retail: float):
        """
        Evaluates all active alert rules against current rates and triggers if conditions met.
        """
        alerts = get_alerts()
        triggered = []

        conn = get_db_connection()
        cursor = conn.cursor()

        for alert in alerts:
            if not alert["is_active"]:
                continue

            target_val = alert["target_rate"]
            target_type = alert["target_type"] # 'spot' or 'td_retail'
            comparison = alert["comparison"]   # '>=' or '<='
            check_rate = current_spot if target_type == "spot" else td_retail

            is_condition_met = False
            if comparison == ">=" and check_rate >= target_val:
                is_condition_met = True
            elif comparison == "<=" and check_rate <= target_val:
                is_condition_met = True

            if is_condition_met:
                title = f"CAD/USD Rate Alert Triggered! 🎯 ({check_rate:.4f})"
                msg = (
                    f"The CAD/USD {target_type.upper()} rate has reached {check_rate:.4f} "
                    f"(Target: {comparison} {target_val:.4f}). "
                    f"Feasible time to review your CAD to USD transfer!"
                )
                
                # Send notification
                self.send_notification(
                    title=title,
                    message=msg,
                    channel=alert["channel"],
                    rate_val=check_rate,
                    webhook_url=alert["webhook_url"]
                )

                # Update trigger status in database
                now_str = datetime.now().isoformat()
                new_count = alert["trigger_count"] + 1
                cursor.execute("""
                UPDATE alert_rules
                SET triggered_at = ?, trigger_count = ?, is_active = 0
                WHERE id = ?
                """, (now_str, new_count, alert["id"]))

                triggered.append({
                    "alert_id": alert["id"],
                    "target_rate": target_val,
                    "actual_rate": check_rate,
                    "target_type": target_type
                })

        conn.commit()
        conn.close()
        return triggered
