#!/usr/bin/env python3
"""
Kick Stream Notifier - TELEGRAM SPAM VERSION (MULTI STREAM + STATUS COMMAND)
"""

import requests
import time
import os
from datetime import datetime
import threading

# ============= CONFIGURATION =============
KICK_USERNAMES = os.getenv("KICK_USERNAMES", "jamie").split(",")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
SPAM_INTERVAL = 10
# =========================================


class TelegramBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0
        self.is_spamming = False
        self.spam_thread = None
        self.monitor = None

    def send_message(self, text):
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

    def handle_commands(self):
        """Handle Telegram commands"""
        while True:
            try:
                command = self.get_updates()
                if command:
                    print(f"📩 Command received: {command}")

                    if command == "/status":
                        status = self.monitor.get_status()
                        self.send_message(status)

                    elif command.startswith("/add "):
                        username = command.split("/add ")[1].strip()
                        self.monitor.add_streamer(username)
                        self.send_message(f"✅ Added <b>{username}</b> to monitoring list")

                    elif command.startswith("/remove "):
                        username = command.split("/remove ")[1].strip()
                        self.monitor.remove_streamer(username)
                        self.send_message(f"❌ Removed <b>{username}</b>")

                    elif command == "/list":
                        streamers = ", ".join(self.monitor.usernames)
                        self.send_message(f"📺 Monitoring:\n<b>{streamers}</b>")

                time.sleep(1)
            except Exception as e:
                print(f"❌ Command handler error: {e}")
                time.sleep(5)

    def spam_user(self, username, stream_title, stream_url):
        spam_count = 0
        while self.is_spamming:
            spam_count += 1
            message = f"""
🚨🚨🚨 <b>WAKE UP!</b> 🚨🚨🚨

🔴 <b>{username.upper()} IS LIVE RIGHT NOW!</b>

📺 Stream: {stream_title}
🎮 Watch: {stream_url}

⏰ Spam #{spam_count}

<b>Reply "awake" to stop these messages!</b>
"""
            self.send_message(message)

            for _ in range(SPAM_INTERVAL):
                time.sleep(1)
                response = self.get_updates()
                if response and ("awake" in response or "stop" in response or "ok" in response):
                    self.is_spamming = False
                    self.send_message("✅ <b>Okay! I'll stop spamming you now.</b>")
                    return

    def start_spam(self, username, stream_title, stream_url):
        if not self.is_spamming:
            self.is_spamming = True
            self.spam_thread = threading.Thread(
                target=self.spam_user,
                args=(username, stream_title, stream_url),
                daemon=True
            )
            self.spam_thread.start()

    def stop_spam(self):
        self.is_spamming = False


class KickMonitor:
    def __init__(self, usernames):
        self.usernames = [u.strip() for u in usernames]
        self.live_status = {username: False for username in self.usernames}

    def add_streamer(self, username):
        if username not in self.usernames:
            self.usernames.append(username)
            self.live_status[username] = False

    def remove_streamer(self, username):
        if username in self.usernames:
            self.usernames.remove(username)
            del self.live_status[username]

    def get_status(self):
        message = "📊 <b>Bot Status</b>\n\n"
        for username in self.usernames:
            status = "🔴 Live" if self.live_status.get(username) else "⚫ Offline"
            message += f"{username}: {status}\n"
        return message

    def check_stream_status(self, username):
        try:
            url = f"https://kick.com/api/v2/channels/{username}"
            headers = {
                'User-Agent': 'Mozilla/5.0'
            }
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                livestream = data.get('livestream')
                if livestream and livestream.get('is_live'):
                    stream_title = livestream.get('session_title', 'Untitled Stream')
                    return True, stream_title
                else:
                    return False, None

            return None, None
        except Exception as e:
            print(f"❌ Error checking {username}: {e}")
            return None, None


def main():
    print("🚨 Kick Multi Stream Notifier 🚨")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram config missing")
        return

    bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    monitor = KickMonitor(KICK_USERNAMES)
    bot.monitor = monitor

    bot.send_message("✅ Bot started!\n\nCommands:\n/status\n/add username\n/remove username\n/list")

    command_thread = threading.Thread(target=bot.handle_commands, daemon=True)
    command_thread.start()

    while True:
        try:
            for username in monitor.usernames:
                is_live, stream_title = monitor.check_stream_status(username)

                if is_live is None:
                    continue

                if is_live and not monitor.live_status[username]:
                    print(f"🔴 {username} went live")
                    bot.start_spam(username, stream_title, f"https://kick.com/{username}")
                    monitor.live_status[username] = True

                elif not is_live and monitor.live_status[username]:
                    print(f"⚫ {username} ended")
                    bot.stop_spam()
                    monitor.live_status[username] = False

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
