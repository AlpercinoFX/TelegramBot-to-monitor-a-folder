import time
import os
import sys
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

class NewFileHandler(FileSystemEventHandler):
    def __init__(self, excluded_files, bot_token, chat_id):
        super().__init__()
        self.excluded_files = excluded_files
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_telegram_message(self, message, file_path=None):
        if self.bot_token and self.chat_id:  # Only send if both are available
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message
            }
            
            # Send the message
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                print("Message sent successfully!")
            else:
                print(f"Failed to send message: {response.status_code} - {response.text}")

            # If a file path is provided, send the file as an attachment
            if file_path:
                self.send_document(file_path)

    def send_document(self, file_path):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
        with open(file_path, 'rb') as file:
            files = {'document': file}
            payload = {'chat_id': self.chat_id}
            response = requests.post(url, data=payload, files=files)
            if response.status_code == 200:
                print(f"File {file_path} sent successfully!")
            else:
                print(f"Failed to send file: {response.status_code} - {response.text}")

    def on_created(self, event):
        # Check if the created event is for a file and not in the excluded list
        if not event.is_directory:
            file_name = os.path.basename(event.src_path)  # Get the file name from the path
            if file_name in self.excluded_files:
                print(f"Excluded file created: {event.src_path}")
                return  # Skip processing this file
            
            message = f"New file created: {file_name}"  # Send only the file name
            print(message)
            self.send_telegram_message(message, event.src_path)  # Send message and file to Telegram

def monitor_directory(path, excluded_files, bot_token, chat_id):
    event_handler = NewFileHandler(excluded_files, bot_token, chat_id)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)  # Keep the script running
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def send_monitoring_message(bot_token, chat_id, interval, worker):
    while True:
        time.sleep(interval)  # Wait for the specified interval
        message = f"Monitoring is still active by worker: {worker}."  # Include worker name
        print(message)
        if bot_token and chat_id:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message
            }
            requests.post(url, json=payload)  # Send the monitoring message

def read_config(file_path):
    config = {}
    try:
        with open(file_path, 'r') as file:
            for line in file:
                if ':' in line:  # Check if the line contains a colon
                    key, value = line.split(':', 1)  # Split on the first ':'
                    config[key.strip()] = value.strip()  # Store key-value pairs in the dictionary
        return (
            config.get('BotToken'),
            config.get('ChatID'),
            [file.strip() for file in config.get('ExcludedFiles', '').split(',') if file.strip()],
            config.get('Worker'),
            int(config.get('MonitoringInterval', 10))  # Default to 10 seconds if not set
        )
    except Exception as e:
        print(f"Could not read config file: {e}")
        return None, None, [], None, 10  # Return 10 seconds as default for MonitoringInterval if there is an issue

if __name__ == "__main__":
    directory_to_monitor = os.path.dirname(os.path.abspath(sys.argv[0]))  # Get the directory of the current script

    # Read bot token, chat ID, excluded files, worker, and monitoring interval from config.txt
    config_file_path = os.path.join(directory_to_monitor, 'TelegramBotSettings.txt')
    BOT_TOKEN, CHAT_ID, EXCLUDED_FILES, WORKER, MONITORING_INTERVAL = read_config(config_file_path)

    # Send a startup message if bot_token and chat_id are available
    if BOT_TOKEN and CHAT_ID:
        startup_message = f"Monitoring has started successfully by worker: {WORKER}. Monitoring interval is set to {MONITORING_INTERVAL} seconds."  # Include worker name and interval
        print(startup_message)
        # Send startup message to Telegram
        NewFileHandler(EXCLUDED_FILES, BOT_TOKEN, CHAT_ID).send_telegram_message(startup_message)
        
        # Start a thread for sending periodic monitoring messages with worker name
        threading.Thread(target=send_monitoring_message, args=(BOT_TOKEN, CHAT_ID, MONITORING_INTERVAL, WORKER), daemon=True).start()
    else:
        print("Monitoring has started, but credentials are not available for Telegram notifications.")

    # Run the monitoring in the foreground
    monitor_directory(directory_to_monitor, EXCLUDED_FILES, BOT_TOKEN, CHAT_ID)

    # You can use WORKER as needed in your script
    print(f"Worker username loaded: {WORKER}")
