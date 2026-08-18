#!/usr/bin/env python3
"""
LooniePulse FX - Autonomous 24/7 Cloud Tracker & Daily Morning Email Briefing
Runs serverlessly in GitHub Actions / Cloud Cron without needing any local computer.
"""

import os
import sys
import json
import urllib.request
import urllib.error
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core.rate_fetcher import RateFetcher
from core.analyzer import Analyzer
from core.recommender import Recommender

def send_ntfy_json(topic: str, email_to: str, title: str, message: str, tags: list):
    """
    Sends push notification and email via ntfy.sh JSON API.
    """
    target_topic = topic or "looniepulse_fx_briefings"
    try:
        url = "https://ntfy.sh"
        payload = {
            "topic": target_topic,
            "title": title,
            "message": message,
            "priority": 4,
            "tags": tags
        }
        if email_to:
            payload["email"] = email_to

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "LooniePulse-FX-Agent/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            if resp.status == 200:
                return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        print(f"[Cloud Notifier] ntfy HTTP {e.code} Error: {error_body}")
        return False
    except Exception as e:
        print(f"[Cloud Notifier] ntfy general error: {e}")
        return False

def send_smtp_email(smtp_user: str, smtp_pass: str, to_email: str, title: str, text_content: str, smtp_host: str = "smtp.gmail.com", smtp_port: int = 587):
    """
    Sends a formatted email via standard SMTP (e.g. Gmail, Outlook, AWS SES).
    """
    if not smtp_user or not smtp_pass or not to_email:
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = title
        msg['From'] = f"LooniePulse FX <{smtp_user}>"
        msg['To'] = to_email

        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:#f4f6f9; padding:24px;">
          <div style="max-width:600px; margin:0 auto; background:#ffffff; border-radius:12px; overflow:hidden; border:1px solid #e2e8f0; box-shadow:0 4px 12px rgba(0,0,0,0.05);">
            <div style="background:#0f172a; padding:20px; color:#ffffff; text-align:center;">
              <h2 style="margin:0; font-size:1.3rem;">🇨🇦 ➔ 🇺🇸 LooniePulse FX Briefing</h2>
              <p style="margin:4px 0 0 0; font-size:0.85rem; color:#94a3b8;">Autonomous TD CAD to USD Transfer Intelligence</p>
            </div>
            <div style="padding:24px; color:#334155; line-height:1.6;">
              <pre style="font-family:inherit; white-space:pre-wrap; font-size:0.95rem; margin:0; line-height:1.6;">{text_content}</pre>
            </div>
            <div style="background:#f8fafc; padding:14px; text-align:center; font-size:0.75rem; color:#94a3b8; border-top:1px solid #e2e8f0;">
              LooniePulse FX 24/7 Autonomous Cloud Tracker • Bank of Canada & Interbank Spot Feed
            </div>
          </div>
        </div>
        """
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
        server.starttls()
        # Clean any whitespace from app password
        clean_pass = smtp_pass.replace(" ", "").strip()
        server.login(smtp_user.strip(), clean_pass)
        server.sendmail(smtp_user.strip(), [to_email.strip()], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[Cloud Notifier] SMTP Email error: {e}")
        return False

def send_discord_webhook(webhook_url: str, title: str, message: str, rate: float, trend_str: str, rec_badge: str, is_digest: bool = False):
    """
    Sends a rich embed message to a Discord channel.
    """
    if not webhook_url:
        return False
    try:
        color = 3447003 if is_digest else 3066993
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
                "footer": {"text": f"LooniePulse FX 24/7 Cloud Tracker • {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"}
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

def dispatch_notifications(title: str, msg: str, spot: float, trend_str: str, rec_badge: str, is_digest: bool, ntfy_topic: str, alert_email: str, discord_webhook: str, telegram_token: str, telegram_chat_id: str, smtp_user: str, smtp_pass: str, smtp_host: str, smtp_port: int):
    tags = ["sunrise", "chart_with_upwards_trend"] if is_digest else ["rotating_light", "moneybag"]
    notified_any = False

    # 1. Direct SMTP Email (if SMTP_USER and SMTP_PASS are set)
    if smtp_user and smtp_pass and alert_email:
        if send_smtp_email(smtp_user, smtp_pass, alert_email, title, msg, smtp_host, smtp_port):
            print(f"✅ Direct SMTP Email successfully delivered to {alert_email}")
            notified_any = True

    # 2. JSON ntfy.sh delivery (Phone Push & Email Relay)
    if ntfy_topic or (alert_email and not (smtp_user and smtp_pass)):
        if send_ntfy_json(ntfy_topic, alert_email, title, msg, tags):
            if alert_email:
                print(f"✅ Email notification dispatched to {alert_email} via ntfy relay")
            if ntfy_topic:
                print(f"✅ Phone push notification dispatched to topic: {ntfy_topic}")
            notified_any = True

    # 3. Discord Webhook
    if discord_webhook:
        if send_discord_webhook(discord_webhook, title, msg, spot, trend_str, rec_badge, is_digest):
            print("✅ Notification posted to Discord channel")
            notified_any = True

    # 4. Telegram
    if telegram_token and telegram_chat_id:
        tg_msg = f"*{title}*\n\n{msg}"
        if send_telegram_alert(telegram_token, telegram_chat_id, tg_msg):
            print("✅ Notification sent to Telegram")
            notified_any = True

    if not notified_any:
        print("⚠️ Could not deliver notification. Please check that ALERT_EMAIL, NTFY_TOPIC, DISCORD, or SMTP credentials are valid.")

def run_cloud_check(force_digest: bool = False):
    # Read environment variables
    target_rate = float(os.getenv("TARGET_RATE", "0.7300"))
    force_notify = os.getenv("FORCE_NOTIFY", "false").lower() in ("true", "1") or force_digest
    daily_digest_env = os.getenv("DAILY_DIGEST", "false").lower() in ("true", "1")
    
    # Morning Digest hour: 13 UTC = 9:00 AM EDT / 8:00 AM CDT / 6:00 AM PDT
    digest_hour_utc = int(os.getenv("DIGEST_HOUR_UTC", "13"))
    current_utc_hour = datetime.utcnow().hour
    is_morning_window = (current_utc_hour == digest_hour_utc) or daily_digest_env or force_digest

    alert_email = os.getenv("ALERT_EMAIL", "") or os.getenv("NOTIFICATION_EMAIL", "")
    ntfy_topic = os.getenv("NTFY_TOPIC", "")
    discord_webhook = os.getenv("DISCORD_WEBHOOK", "")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    print(f"=== [24/7 LooniePulse Cloud Tracker] ===")
    print(f"🕒 UTC Timestamp:   {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🎯 Target Alert:    CAD/USD >= {target_rate:.4f}")
    print(f"📬 Target Email:    {alert_email or '(None configured)'}")
    print(f"🔑 SMTP Configured: {'YES (' + smtp_user + ')' if (smtp_user and smtp_pass) else 'NO (Using relay / push)'}")
    print(f"🌅 Morning Window:  {'ACTIVE (Sending Daily Digest)' if is_morning_window else 'Inactive (Standard Watcher Run)'}")

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

    print(f"📊 Live Spot:       1 CAD = ${spot:.4f} USD ({trend_str}) | USD/CAD: {usdcad:.4f}")
    print(f"🏦 TD Retail:       1 CAD = ${td_retail:.4f} USD (-2.65% spread)")
    print(f"⚡ Norbert's:       1 CAD = ${norbert:.4f} USD")
    print(f"📈 Feasibility:     {verdict_badge} (Score: {rec['feasibility_score']}/100, 10Y Percentile: {p10}%)")

    is_breached = spot >= target_rate
    print(f"⚡ Target Breached:  {'✅ YES' if is_breached else '❌ NO (Below target)'}")

    # Case 1: Target rate breached (Instant Priority Alert)
    if is_breached:
        title = f"🎯 CAD/USD TARGET REACHED: {spot:.4f} USD!"
        msg = (
            f"The CAD to USD exchange rate has crossed your target threshold of {target_rate:.4f}!\n\n"
            f"• Interbank Spot: 1 CAD = ${spot:.4f} USD ({trend_str})\n"
            f"• TD EasyWeb Retail: ${td_retail:.4f} USD\n"
            f"• Norbert's Gambit: ${norbert:.4f} USD (Save +$900+ on $50k CAD)\n\n"
            f"💡 Strategy Verdict: {rec['action_advice']}"
        )
        dispatch_notifications(title, msg, spot, trend_str, verdict_badge, False, ntfy_topic, alert_email, discord_webhook, telegram_token, telegram_chat_id, smtp_user, smtp_pass, smtp_host, smtp_port)

    # Case 2: Daily Morning Digest (Heartbeat & Daily Trend Briefing)
    elif is_morning_window or force_notify:
        title = f"☀️ CAD/USD Morning Briefing • {spot:.4f} USD"
        msg = (
            f"🟢 24/7 Tracker Active • {datetime.now().strftime('%b %d, %Y')}\n\n"
            f"📊 Daily Trend: {trend_icon} {trend_str} (USD/CAD: {usdcad:.4f})\n"
            f"• Spot Rate: 1 CAD = ${spot:.4f} USD\n"
            f"• TD EasyWeb Retail: ${td_retail:.4f} USD (-2.65% spread)\n"
            f"• Norbert's Gambit (TD DI): ${norbert:.4f} USD\n\n"
            f"🎯 10-Yr Position: {p10}% ({verdict_badge})\n"
            f"🔔 Active Watcher: Alert will trigger when Spot reaches >= {target_rate:.4f} USD.\n\n"
            f"💡 Recommended Strategy:\n{rec['action_advice']}"
        )
        dispatch_notifications(title, msg, spot, trend_str, verdict_badge, True, ntfy_topic, alert_email, discord_webhook, telegram_token, telegram_chat_id, smtp_user, smtp_pass, smtp_host, smtp_port)

    else:
        print("ℹ️ Standard 30-min watcher run complete. No threshold breached.")

if __name__ == "__main__":
    is_digest = "--digest" in sys.argv
    run_cloud_check(force_digest=is_digest)
