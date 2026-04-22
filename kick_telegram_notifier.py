#!/usr/bin/env python3
"""
Kick Stream Notifier - TELEGRAM SPAM VERSION
Spams you on Telegram until you respond "awake" when Jamie goes live!
"""

import requests
import time
import os
from datetime import datetime
import threading

# ============= CONFIGURATION =============
KICK_USERNAME = os.getenv("KICK_USERNAME", "jamie")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")  # You'll get this from BotFather
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")  # Your personal chat ID
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
SPAM_INTERVAL = 10  # Spam every 10 seconds until you respond
# =========================================


class TelegramBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0
        self.is_spamming = False
        self.spam_thread = None
        
    def send_message(self, text):
        """Send a message to the user"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return False
    
    def get_updates(self):
        """Check for new messages from user"""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {"offset": self.last_update_id + 1, "timeout": 1}
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data["ok"] and data["result"]:
                    for update in data["result"]:
                        self.last_update_id = update["update_id"]
                        if "message" in update and "text" in update["message"]:
                            return update["message"]["text"].lower().strip()
            return None
        except Exception as e:
            print(f"❌ Error checking messages: {e}")
            return None
    
    def spam_user(self, stream_title, stream_url):
        """Spam the user until they respond"""
        spam_count = 0
        while self.is_spamming:
            spam_count += 1
            message = f"""
🚨🚨🚨 <b>WAKE UP!</b> 🚨🚨🚨

🔴 <b>JAMIE IS LIVE RIGHT NOW!</b>

📺 Stream: {stream_title}
🎮 Watch: {stream_url}

⏰ Spam #{spam_count}

<b>Reply "awake" to stop these messages!</b>
"""
            self.send_message(message)
            
            # Check if user responded
            for _ in range(SPAM_INTERVAL):
                time.sleep(1)
                response = self.get_updates()
                if response and ("awake" in response or "stop" in response or "ok" in response):
                    self.is_spamming = False
                    self.send_message("✅ <b>Okay! I'll stop spamming you now.</b>\n\nEnjoy the stream! 🎮")
                    print(f"✅ User responded: {response}")
                    return
    
    def start_spam(self, stream_title, stream_url):
        """Start spamming in a separate thread"""
        if not self.is_spamming:
            self.is_spamming = True
            self.spam_thread = threading.Thread(
                target=self.spam_user, 
                args=(stream_title, stream_url),
                daemon=True
            )
            self.spam_thread.start()
    
    def stop_spam(self):
        """Stop spamming"""
        self.is_spamming = False


class KickMonitor:
    def __init__(self, username):
        self.username = username
        self.is_live = False
        self.api_url = f"https://kick.com/api/v2/channels/{username}"
        
    def check_stream_status(self):
        """Check if the streamer is currently live"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(self.api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                livestream = data.get('livestream')
                if livestream and livestream.get('is_live'):
                    stream_title = livestream.get('session_title', 'Untitled Stream')
                    return True, stream_title
                else:
                    return False, None
            else:
                print(f"⚠️  API returned status {response.status_code}")
                return None, None
                
        except Exception as e:
            print(f"❌ Error checking stream: {e}")
            return None, None


def main():
    print("=" * 70)
    print("🚨 KICK STREAM NOTIFIER - TELEGRAM SPAM VERSION 🚨")
    print("=" * 70)
    print(f"👤 Monitoring: {KICK_USERNAME}")
    print(f"📱 Telegram Bot Token: {TELEGRAM_BOT_TOKEN[:20]}..." if TELEGRAM_BOT_TOKEN else "❌ NOT SET!")
    print(f"💬 Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"⏱️  Check interval: {CHECK_INTERVAL} seconds")
    print(f"🔔 Spam interval: {SPAM_INTERVAL} seconds (until you reply 'awake')")
    print("=" * 70)
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n❌ ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set!")
        print("Please follow the setup guide to get these values.")
        return
    
    print("\n🚀 Starting monitor...")
    print("-" * 70)
    
    bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    monitor = KickMonitor(KICK_USERNAME)
    
    # Send startup message
    bot.send_message(f"✅ <b>Bot started!</b>\n\nMonitoring <b>{KICK_USERNAME}</b> on Kick.\nI'll spam you when they go live! 🔔")
    
    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            is_live, stream_title = monitor.check_stream_status()
            
            if is_live is None:
                print(f"[{current_time}] ⏳ Retrying...")
                
            elif is_live and not monitor.is_live:
                # Stream just went live! START SPAMMING!
                print(f"[{current_time}] 🔴 STREAM WENT LIVE!")
                print(f"              Title: {stream_title}")
                print(f"              🚨 STARTING SPAM ALARM!")
                
                stream_url = f"https://kick.com/{monitor.username}"
                bot.start_spam(stream_title, stream_url)
                monitor.is_live = True
                
            elif not is_live and monitor.is_live:
                # Stream went offline
                print(f"[{current_time}] ⚫ Stream ended")
                bot.stop_spam()
                bot.send_message("⚫ <b>Stream ended</b>\n\nJamie is no longer live.")
                monitor.is_live = False
                
            elif is_live:
                # Still live
                print(f"[{current_time}] 🔴 Live: {stream_title}")
                
            else:
                # Still offline
                print(f"[{current_time}] ⚫ Offline - waiting...")
            
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n👋 Stopping monitor...")
            bot.send_message("👋 <b>Bot stopped</b>\n\nNo longer monitoring streams.")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
