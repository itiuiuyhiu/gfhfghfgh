#!/usr/bin/env python3
"""
Kick Stream Notifier - FIXED TELEGRAM VERSION with Commands
- Spams until you ACTUALLY respond (bug fixed!)
- Monitor multiple streamers
- Commands: /status, /test, /add, /remove, /list
"""

import requests
import time
import os
from datetime import datetime
import threading
import json

# ============= CONFIGURATION =============
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
SPAM_INTERVAL = 10  # Spam every 10 seconds until you respond
STREAMERS_FILE = "/tmp/streamers.json"  # Persistent storage for streamer list
# =========================================


class TelegramBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0
        self.spam_threads = {}  # Track spam threads per streamer
        
    def send_message(self, text):
        """Send a message to the user"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return False
    
    def get_updates(self):
        """Check for new messages from user - returns list of messages"""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {"offset": self.last_update_id + 1, "timeout": 1}
            response = requests.get(url, params=params, timeout=5)
            
            messages = []
            if response.status_code == 200:
                data = response.json()
                if data["ok"] and data["result"]:
                    for update in data["result"]:
                        self.last_update_id = update["update_id"]
                        if "message" in update and "text" in update["message"]:
                            messages.append(update["message"]["text"].strip())
            return messages
        except Exception as e:
            print(f"❌ Error checking messages: {e}")
            return []
    
    def spam_user(self, streamer_name, stream_title, stream_url):
        """Spam the user until they respond - FIXED VERSION"""
        spam_count = 0
        print(f"🚨 Starting spam thread for {streamer_name}")
        
        while self.spam_threads.get(streamer_name, False):
            spam_count += 1
            message = f"""
🚨🚨🚨 <b>WAKE UP!</b> 🚨🚨🚨

🔴 <b>{streamer_name.upper()} IS LIVE RIGHT NOW!</b>

📺 Stream: {stream_title}
🎮 Watch: {stream_url}

⏰ Spam #{spam_count}

<b>Reply "awake" or "stop" to stop these messages!</b>
"""
            self.send_message(message)
            print(f"📢 Spam #{spam_count} sent for {streamer_name}")
            
            # Check for user response every second for SPAM_INTERVAL seconds
            for i in range(SPAM_INTERVAL):
                time.sleep(1)
                messages = self.get_updates()
                
                for msg in messages:
                    msg_lower = msg.lower()
                    # Check if user is trying to stop spam
                    if any(word in msg_lower for word in ["awake", "stop", "ok", "shut up", "quiet"]):
                        self.spam_threads[streamer_name] = False
                        self.send_message(f"✅ <b>Okay! Stopped spamming about {streamer_name}.</b>\n\nEnjoy the stream! 🎮")
                        print(f"✅ User responded to stop spam for {streamer_name}: {msg}")
                        return
        
        print(f"🛑 Spam thread ended for {streamer_name}")
    
    def start_spam(self, streamer_name, stream_title, stream_url):
        """Start spamming in a separate thread"""
        if streamer_name not in self.spam_threads or not self.spam_threads[streamer_name]:
            self.spam_threads[streamer_name] = True
            thread = threading.Thread(
                target=self.spam_user, 
                args=(streamer_name, stream_title, stream_url),
                daemon=True
            )
            thread.start()
            print(f"✅ Spam thread started for {streamer_name}")
    
    def stop_spam(self, streamer_name):
        """Stop spamming for a specific streamer"""
        if streamer_name in self.spam_threads:
            self.spam_threads[streamer_name] = False
            print(f"🛑 Stopping spam for {streamer_name}")


class StreamerManager:
    def __init__(self, filepath):
        self.filepath = filepath
        self.streamers = self.load_streamers()
    
    def load_streamers(self):
        """Load streamers from file or create default"""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r') as f:
                    return json.load(f)
            else:
                # Default: just Jamie
                default = ["jamie"]
                self.save_streamers(default)
                return default
        except Exception as e:
            print(f"❌ Error loading streamers: {e}")
            return ["jamie"]
    
    def save_streamers(self, streamers=None):
        """Save streamers to file"""
        try:
            if streamers is None:
                streamers = self.streamers
            with open(self.filepath, 'w') as f:
                json.dump(streamers, f)
        except Exception as e:
            print(f"❌ Error saving streamers: {e}")
    
    def add_streamer(self, username):
        """Add a streamer to the list"""
        username = username.lower().strip()
        if username not in self.streamers:
            self.streamers.append(username)
            self.save_streamers()
            return True
        return False
    
    def remove_streamer(self, username):
        """Remove a streamer from the list"""
        username = username.lower().strip()
        if username in self.streamers:
            self.streamers.remove(username)
            self.save_streamers()
            return True
        return False
    
    def get_streamers(self):
        """Get list of all streamers"""
        return self.streamers.copy()


class KickMonitor:
    def __init__(self):
        self.live_status = {}  # Track who's live: {username: (is_live, stream_title)}
        
    def check_stream_status(self, username):
        """Check if a streamer is currently live"""
        try:
            api_url = f"https://kick.com/api/v2/channels/{username}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                livestream = data.get('livestream')
                if livestream and livestream.get('is_live'):
                    stream_title = livestream.get('session_title', 'Untitled Stream')
                    return True, stream_title
                else:
                    return False, None
            else:
                print(f"⚠️  API returned status {response.status_code} for {username}")
                return None, None
                
        except Exception as e:
            print(f"❌ Error checking {username}: {e}")
            return None, None
    
    def update_status(self, username, is_live, stream_title=None):
        """Update the live status for a streamer"""
        self.live_status[username] = (is_live, stream_title)
    
    def get_status(self, username):
        """Get the live status for a streamer"""
        return self.live_status.get(username, (False, None))


def handle_commands(bot, manager, monitor, message):
    """Handle bot commands"""
    if not message.startswith('/'):
        return False
    
    parts = message.split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    
    if command == '/status':
        streamers = manager.get_streamers()
        if not streamers:
            bot.send_message("📊 <b>Status</b>\n\nNo streamers being monitored.")
            return True
        
        status_lines = ["📊 <b>Monitoring Status</b>\n"]
        for username in streamers:
            is_live, stream_title = monitor.get_status(username)
            if is_live:
                status_lines.append(f"🔴 <b>{username}</b> - LIVE\n   📺 {stream_title}")
            else:
                status_lines.append(f"⚫ <b>{username}</b> - Offline")
        
        bot.send_message("\n".join(status_lines))
        return True
    
    elif command == '/test':
        bot.send_message("🧪 <b>Test notification</b>\n\nIf you see this, notifications are working! ✅")
        return True
    
    elif command == '/add':
        if not arg:
            bot.send_message("❌ Usage: /add <username>\n\nExample: /add xqc")
            return True
        
        username = arg.lower().strip()
        if manager.add_streamer(username):
            bot.send_message(f"✅ Added <b>{username}</b> to monitoring list!\n\nI'll spam you when they go live.")
        else:
            bot.send_message(f"⚠️ <b>{username}</b> is already being monitored.")
        return True
    
    elif command == '/remove':
        if not arg:
            bot.send_message("❌ Usage: /remove <username>\n\nExample: /remove xqc")
            return True
        
        username = arg.lower().strip()
        if manager.remove_streamer(username):
            bot.send_message(f"✅ Removed <b>{username}</b> from monitoring list.")
        else:
            bot.send_message(f"⚠️ <b>{username}</b> is not in the monitoring list.")
        return True
    
    elif command == '/list':
        streamers = manager.get_streamers()
        if not streamers:
            bot.send_message("📋 <b>Streamer List</b>\n\nNo streamers being monitored.\n\nUse /add <username> to add one!")
            return True
        
        streamer_list = "\n".join([f"• {s}" for s in streamers])
        bot.send_message(f"📋 <b>Monitoring {len(streamers)} streamer(s):</b>\n\n{streamer_list}\n\n<i>Use /add or /remove to manage the list.</i>")
        return True
    
    elif command == '/help':
        help_text = """
🤖 <b>Bot Commands</b>

/status - Check who's live right now
/test - Send a test notification
/add <username> - Add a streamer to monitor
/remove <username> - Remove a streamer
/list - Show all monitored streamers
/help - Show this help message

<i>When a streamer goes live, I'll spam you until you reply "awake"!</i>
"""
        bot.send_message(help_text)
        return True
    
    return False


def main():
    print("=" * 70)
    print("🚨 KICK STREAM NOTIFIER - FIXED & ENHANCED VERSION 🚨")
    print("=" * 70)
    print(f"📱 Telegram Bot Token: {TELEGRAM_BOT_TOKEN[:20]}..." if TELEGRAM_BOT_TOKEN else "❌ NOT SET!")
    print(f"💬 Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"⏱️  Check interval: {CHECK_INTERVAL} seconds")
    print(f"🔔 Spam interval: {SPAM_INTERVAL} seconds (until you reply)")
    print("=" * 70)
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n❌ ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set!")
        return
    
    bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    manager = StreamerManager(STREAMERS_FILE)
    monitor = KickMonitor()
    
    # Send startup message
    streamers = manager.get_streamers()
    streamer_list = ", ".join(streamers)
    bot.send_message(f"✅ <b>Bot started!</b>\n\nMonitoring: <b>{streamer_list}</b>\n\nI'll spam you when they go live! 🔔\n\n<i>Type /help for commands</i>")
    
    print(f"\n🚀 Monitoring {len(streamers)} streamer(s): {streamer_list}")
    print("-" * 70)
    
    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check for commands
            messages = bot.get_updates()
            for msg in messages:
                if handle_commands(bot, manager, monitor, msg):
                    print(f"[{current_time}] ⌨️  Command received: {msg}")
            
            # Check all streamers
            streamers = manager.get_streamers()
            for username in streamers:
                is_live, stream_title = monitor.check_stream_status(username)
                was_live, old_title = monitor.get_status(username)
                
                if is_live is None:
                    # API error, skip this streamer
                    continue
                
                elif is_live and not was_live:
                    # Stream just went live! START SPAMMING!
                    print(f"[{current_time}] 🔴 {username.upper()} WENT LIVE!")
                    print(f"              Title: {stream_title}")
                    
                    stream_url = f"https://kick.com/{username}"
                    bot.start_spam(username, stream_title, stream_url)
                    monitor.update_status(username, True, stream_title)
                    
                elif not is_live and was_live:
                    # Stream went offline
                    print(f"[{current_time}] ⚫ {username} stream ended")
                    bot.stop_spam(username)
                    bot.send_message(f"⚫ <b>Stream ended</b>\n\n{username} is no longer live.")
                    monitor.update_status(username, False, None)
                    
                elif is_live and was_live:
                    # Still live
                    print(f"[{current_time}] 🔴 {username} still live: {stream_title}")
                    monitor.update_status(username, True, stream_title)
                    
                else:
                    # Still offline
                    print(f"[{current_time}] ⚫ {username} offline")
                    monitor.update_status(username, False, None)
            
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
