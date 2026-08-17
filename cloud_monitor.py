#!/usr/bin/env python3
"""
LooniePulse FX - Autonomous 24/7 Cloud Tracker & Daily Morning Briefing
Runs serverlessly in GitHub Actions / Cloud Cron without needing any local computer.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core.rate_fetcher import RateFetcher
from core.analyzer import Analyzer
from core.recommender import Recommender

def send_ntfy_push(topic: str, title: str, message: str, tags: str = "chart_with_upwards_trend,moneybag"):
    """
    Sends an instant push notification to mobile phone via ntfy.sh (No signup required).
    """
    if not topic:
        return False
    try:
        url = f"https://ntfy.sh/{topic}"
        clean_title = title.encode('ascii', 'ignore').decode('ascii').strip() or "CAD/USD Rate Update"
        req = urllib.request.Request(
            url,
            data=message.encode('utf-8'),
            headers={
                "Title": clean_title,
                "Priority": "high",
                "Tags": tags
            }
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[Cloud Notifier] ntfy push error: {e}")
        return False

def send_discord_webhook(webhook_url: str, title: str, message: str, rate: float, trend_str: str, rec_badge: str, is_digest: bool = False):
    """
    Sends a rich embed message to a Discord channel.
    """
    if not webhook_url:
        return False
    try:
        color = 3447003 if is_digest else 3066993 # Blue for digest, Green for alert
        payload = {
            "username": "LooniePulse Cloud Agent",
            "avatar_url": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f1e8-1f1e6.png",
            "content": f"{'☀️' if is_digest else '🚨'} **{title}**",
            "embeds": [{
                "title": f"CAD/USD Spot: {rate:.4f} USD ({trend_str})",
                "description": message,
                "color": color,
                "fields": [
                    {"name": "Interbank Spot", "value": f"1 CAD = ${rate:.4f} USD", "inline": True},
                    {"name": "TD Retail (-2.65%)", "value": f"${rate * (1 - 0.0265):.4f} USD", "inline": True},
                    {"name": "Norbert's Gambit", "value": f"${rate * (1 - 0.0010):.4f} USD", "inline": True},
                    {"name": "Market Verdict", "value": f"`{rec_badge}`", "inline": True}
                ],
                "footer": {"text": f"LooniePulse FX 24/7 Cloud Tracker • {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"}
            }]
        }
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'User-Agent': 'LooniePulse-Cloud-Agent'}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"[Cloud Notifier] Discord error: {e}")
        return False

def send_telegram_alert(bot_token: str, chat_id: str, message: str):
    """
    Sends an instant message via Telegram Bot API.
    """
    if not bot_token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[Cloud Notifier] Telegram error: {e}")
        return False

def dispatch_notifications(title: str, msg: str, spot: float, trend_str: str, rec_badge: str, is_digest: bool, ntfy_topic: str, discord_webhook: str, telegram_token: str, telegram_chat_id: str):
    tags = "sunrise,chart_with_upwards_trend" if is_digest else "rotating_light,moneybag"
    notified_any = False

    # 1. ntfy.sh mobile push
    if ntfy_topic:
        if send_ntfy_push(ntfy_topic, title, msg, tags):
            print(f"✅ Push notification sent to phone via ntfy.sh/{ntfy_topic}")
            notified_any = True

    # 2. Discord Webhook
    if discord_webhook:
        if send_discord_webhook(discord_webhook, title, msg, spot, trend_str, rec_badge, is_digest):
            print("✅ Notification posted to Discord channel")
            notified_any = True

    # 3. Telegram
    if telegram_token and telegram_chat_id:
        tg_msg = f"*{title}*\n\n{msg}"
        if send_telegram_alert(telegram_token, telegram_chat_id, tg_msg):
            print("✅ Notification sent to Telegram")
            notified_any = True

    if not notified_any:
        print("⚠️ Notification generated, but no channel (NTFY_TOPIC, DISCORD_WEBHOOK, or TELEGRAM) was configured.")

def run_cloud_check(force_digest: bool = False):
    # Read environment variables
    target_rate = float(os.getenv("TARGET_RATE", "0.7300"))
    force_notify = os.getenv("FORCE_NOTIFY", "false").lower() in ("true", "1") or force_digest
    daily_digest_env = os.getenv("DAILY_DIGEST", "false").lower() in ("true", "1")
    
    # Morning Digest hour: 13 UTC = 9:00 AM EDT / 8:00 AM CDT / 6:00 AM PDT
    digest_hour_utc = int(os.getenv("DIGEST_HOUR_UTC", "13"))
    current_utc_hour = datetime.utcnow().hour
    is_morning_window = (current_utc_hour == digest_hour_utc) or daily_digest_env or force_digest

    ntfy_topic = os.getenv("NTFY_TOPIC", "")
    discord_webhook = os.getenv("DISCORD_WEBHOOK", "")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    print(f"=== [24/7 LooniePulse Cloud Tracker] ===")
    print(f"🕒 UTC Timestamp:  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🎯 Target Alert:   CAD/USD >= {target_rate:.4f}")
    print(f"🌅 Morning Window: {'ACTIVE (Sending Daily Digest)' if is_morning_window else 'Inactive (Standard Watcher Run)'}")

    fetcher = RateFetcher()
    analyzer = Analyzer(fetcher)
    recommender = Recommender(fetcher, analyzer)

    rates = fetcher.get_current_rates()
    spot = rates["spot_cadusd"]
    usdcad = rates["spot_usdcad"]
    td_retail = rates["td_bank"]["retail_rate"]
    norbert = rates["alternatives"]["norberts_gambit"]["effective_rate_raw"]
    change_pct = rates.get("change_pct", 0.0)
    change_usd = rates.get("change_usd", 0.0)

    trend_icon = "📈" if change_pct > 0 else ("📉" if change_pct < 0 else "➡️")
    trend_sign = "+" if change_pct > 0 else ""
    trend_str = f"{trend_sign}{change_pct:.2f}% ({trend_sign}{change_usd:.4f} USD)"

    rec = recommender.generate_recommendation(50000)
    p10 = rec["percentiles"]["percentile_10y"]
    verdict_badge = rec["verdict_badge"]

    print(f"📊 Live Spot:      1 CAD = ${spot:.4f} USD ({trend_str}) | USD/CAD: {usdcad:.4f}")
    print(f"🏦 TD Retail:      1 CAD = ${td_retail:.4f} USD (-2.65% spread)")
    print(f"⚡ Norbert's:      1 CAD = ${norbert:.4f} USD")
    print(f"📈 Feasibility:    {verdict_badge} (Score: {rec['feasibility_score']}/100, 10Y Percentile: {p10}%)")

    is_breached = spot >= target_rate
    print(f"⚡ Target Breached: {'✅ YES' if is_breached else '❌ NO (Below target)'}")

    # Case 1: Target rate breached (Instant Priority Alert)
    if is_breached:
        title = f"🎯 CAD/USD TARGET REACHED: {spot:.4f} USD!"
        msg = (
            f"The CAD to USD exchange rate has crossed your target threshold of {target_rate:.4f}!\n\n"
            f"• Interbank Spot: 1 CAD = ${spot:.4f} USD ({trend_str})\n"
            f"• TD EasyWeb Retail: ${td_retail:.4f} USD\n"
            f"• Norbert's Gambit: ${norbert:.4f} USD (Save +$900+ on $50k)\n\n"
            f"💡 Strategy Verdict: {rec['action_advice']}"
        )
        dispatch_notifications(title, msg, spot, trend_str, verdict_badge, False, ntfy_topic, discord_webhook, telegram_token, telegram_chat_id)

    # Case 2: Daily Morning Digest (Heartbeat & Daily Trend Briefing)
    elif is_morning_window or force_notify:
        title = f"☀️ CAD/USD Morning Briefing • {spot:.4f} USD"
        msg = (
            f"🟢 24/7 Tracker Active • {datetime.now().strftime('%b %d, %Y')}\n\n"
            f"📊 Daily Trend: {trend_icon} {trend_str} (USD/CAD: {usdcad:.4f})\n"
            f"• Spot Rate: 1 CAD = ${spot:.4f} USD\n"
            f"• TD Retail: ${td_retail:.4f} USD (-2.65% spread)\n"
            f"• Norbert's Gambit: ${norbert:.4f} USD\n\n"
            f"🎯 10-Yr Percentile: {p10}% ({verdict_badge})\n"
            f"🔔 Active Watcher: Alert will trigger when Spot reaches >= {target_rate:.4f} USD.\n\n"
            f"💡 Advice: {rec['action_advice']}"
        )
        dispatch_notifications(title, msg, spot, trend_str, verdict_badge, True, ntfy_topic, discord_webhook, telegram_token, telegram_chat_id)

    else:
        print("ℹ️ Standard 30-min watcher run complete. No threshold breached.")

if __name__ == "__main__":
    is_digest = "--digest" in sys.argv
    run_cloud_check(force_digest=is_digest)
