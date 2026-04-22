import os
import sys
import subprocess
import logging
import time
import socket
from flask import Flask
from web.routes import web_bp

CHROME_DEBUG_PORT = 9222
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
]

def is_chrome_debug_running(port=CHROME_DEBUG_PORT):
    """Проверяет, слушает ли кто-то порт 9222."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_chrome_path():
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    return None

def launch_chrome_debug():
    chrome_path = find_chrome_path()
    if not chrome_path:
        print("❌ Chrome не найден. Установите Chrome или укажите путь вручную.")
        return False
    print(f"🚀 Запускаю Chrome с портом отладки {CHROME_DEBUG_PORT}...")
    try:
        subprocess.Popen([
            chrome_path,
            f"--remote-debugging-port={CHROME_DEBUG_PORT}",
            "--user-data-dir=C:\\temp\\chrome_debug_profile"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(10):
            time.sleep(1)
            if is_chrome_debug_running():
                print("✅ Chrome с отладкой запущен.")
                return True
        print("⚠️ Chrome запущен, но порт отладки не отвечает.")
        return True
    except Exception as e:
        print(f"❌ Ошибка запуска Chrome: {e}")
        return False

def open_browser(url):
    import webbrowser
    webbrowser.open(url)

def create_app():
    app = Flask(__name__, template_folder='web/templates', static_folder='web/static')
    app.register_blueprint(web_bp)
    return app

if __name__ == '__main__':
    selenium_logger = logging.getLogger('selenium.webdriver.remote.remote_connection')
    selenium_logger.setLevel(logging.WARNING)

    if not is_chrome_debug_running():
        print("⚠️ Chrome с отладкой не запущен. Пытаюсь запустить...")
        if not launch_chrome_debug():
            print("❌ Не удалось запустить Chrome с отладкой.")
            print("Запустите Chrome вручную с флагом --remote-debugging-port=9222")
            input("Нажмите Enter после запуска...")

    app = create_app()
    print("\n" + "=" * 60)
    print("🚀 likealtuhi v2.0: http://127.0.0.1:5002")
    print("📁 Данные: data/")
    print("🖼️ Изображения: images/")
    print("=" * 60 + "\n")

    import threading
    threading.Timer(1.0, open_browser, args=("http://127.0.0.1:5002",)).start()

    app.run(debug=False, host='127.0.0.1', port=5002, threaded=True)
