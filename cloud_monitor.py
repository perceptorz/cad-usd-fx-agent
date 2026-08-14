#!/usr/bin/env python3
"""
LooniePulse FX - Autonomous 24/7 Cloud Tracker & Notifier
Runs serverlessly in GitHub Actions / Cloud Cron without needing any local computer.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime

# Ensure root dir is in path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core.rate_fetcher import RateFetcher
from core.analyzer import Analyzer
from core.recommender import Recommender

def send_ntfy_push(topic: str, title: str, message: str, rate: float):
    """
    Sends an instant push notification to mobile phone via ntfy.sh (No signup required).
    User just installs the free 'ntfy' app on iOS/Android and subscribes to the topic.
    """
    if not topic:
        return False
    try:
        url = f"https://ntfy.sh/{topic}"
        # Keep headers ASCII-only, place emojis in Tags header and payload
        clean_title = title.encode('ascii', 'ignore').decode('ascii').strip() or "CAD/USD Rate Alert"
        req = urllib.request.Request(
            url,
            data=message.encode('utf-8'),
            headers={
                "Title": clean_title,
                "Priority": "high",
                "Tags": "chart_with_upwards_trend,moneybag"
            }
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[Cloud Notifier] ntfy push error: {e}")
        return False

def send_discord_webhook(webhook_url: str, title: str, message: str, rate: float, rec_summary: str):
    """
    Sends a rich embed message to a Discord channel.
    """
    if not webhook_url:
        return False
    try:
        payload = {
            "username": "LooniePulse Cloud Agent",
            "avatar_url": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f1e8-1f1e6.png",
            "content": f"🚨 **{title}**",
            "embeds": [{
                "title": f"CAD/USD Reached: {rate:.4f} USD",
                "description": f"{message}\n\n**Strategy Recommendation:**\n{rec_summary}",
                "color": 3066993, # Emerald Green
                "fields": [
                    {"name": "Interbank Spot", "value": f"1 CAD = ${rate:.4f} USD", "inline": True},
                    {"name": "TD Retail Rate (-2.65%)", "value": f"${rate * (1 - 0.0265):.4f} USD", "inline": True},
                    {"name": "Norbert's Gambit (TD DI)", "value": f"${rate * (1 - 0.0010):.4f} USD", "inline": True}
                ],
                "footer": {"text": f"LooniePulse FX Cloud Tracker • {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"}
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

def run_cloud_check():
    # Read environment configs
    target_rate = float(os.getenv("TARGET_RATE", "0.7300"))
    force_notify = os.getenv("FORCE_NOTIFY", "false").lower() in ("true", "1")
    
    # Notification channels
    ntfy_topic = os.getenv("NTFY_TOPIC", "")
    discord_webhook = os.getenv("DISCORD_WEBHOOK", "")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    print(f"=== [24/7 LooniePulse Cloud Tracker] ===")
    print(f"🕒 Timestamp:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🎯 Target Rate:   CAD/USD >= {target_rate:.4f}")
    
    fetcher = RateFetcher()
    analyzer = Analyzer(fetcher)
    recommender = Recommender(fetcher, analyzer)

    rates = fetcher.get_current_rates()
    spot = rates["spot_cadusd"]
    td_retail = rates["td_bank"]["retail_rate"]
    norbert = rates["alternatives"]["norberts_gambit"]["effective_rate_raw"]

    print(f"📊 Live Spot:     1 CAD = ${spot:.4f} USD (USD/CAD: {rates['spot_usdcad']:.4f})")
    print(f"🏦 TD Retail:     1 CAD = ${td_retail:.4f} USD")
    print(f"⚡ Norbert Rate:  1 CAD = ${norbert:.4f} USD")

    rec = recommender.generate_recommendation(50000)
    print(f"📈 Feasibility:   {rec['verdict_badge']} (Score: {rec['feasibility_score']}/100)")

    is_breached = spot >= target_rate
    print(f"⚡ Target Breached: {'✅ YES' if is_breached else '❌ NO (Below target)'}")

    if is_breached or force_notify:
        title = f"🎯 CAD/USD Alert: {spot:.4f} USD Reached!"
        msg = (
            f"The CAD to USD rate has reached {spot:.4f} (Target: >= {target_rate:.4f})!\n\n"
            f"• TD Retail EasyWeb: ${td_retail:.4f}\n"
            f"• Norbert's Gambit (TD Direct Investing): ${norbert:.4f}\n\n"
            f"💡 Recommended Action: Use Norbert's Gambit to convert at pure spot and avoid TD's 2.65% spread penalty."
        )

        notified_any = False

        # 1. ntfy.sh instant mobile push
        if ntfy_topic:
            if send_ntfy_push(ntfy_topic, title, msg, spot):
                print(f"✅ Push notification sent to phone via ntfy.sh/{ntfy_topic}")
                notified_any = True

        # 2. Discord Webhook
        if discord_webhook:
            if send_discord_webhook(discord_webhook, title, msg, spot, rec["action_advice"]):
                print("✅ Notification posted to Discord channel")
                notified_any = True

        # 3. Telegram
        if telegram_token and telegram_chat_id:
            tg_msg = f"🚨 *{title}*\n\n{msg}"
            if send_telegram_alert(telegram_token, telegram_chat_id, tg_msg):
                print("✅ Notification sent to Telegram")
                notified_any = True

        if not notified_any:
            print("⚠️ Rate target reached, but no notification channel (NTFY_TOPIC, DISCORD_WEBHOOK, or TELEGRAM) was configured.")
    else:
        print("ℹ️ Rate is currently below target threshold. Next automated cloud check will run in 30 minutes.")

if __name__ == "__main__":
    run_cloud_check()
