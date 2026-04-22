import time
import threading
import requests
import numpy as np
import cv2
import os
import hashlib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from config import IMAGES_DIR, CHROME_DEBUG_PORT, SCROLL_DELAY

class PinterestCollector:
    def __init__(self, data_manager):
        self.dm = data_manager
        self.driver = None
        self.connected = False
        self.is_running = False
        self.thread = None
        self.status = {
            'collected': 0,
            'target': 0,
            'scrolls': 0,
            'category': '',
            'search_term': '',
            'infinite': False,
            'active': False
        }

    def connect(self):
        if self.connected and self.driver:
            try:
                self.driver.current_url
                return True
            except:
                self.connected = False
                self.driver = None

        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{CHROME_DEBUG_PORT}")
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            found = False
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                if "pinterest.com" in self.driver.current_url:
                    found = True
                    break
            if not found:
                print("❌ Не найдена вкладка Pinterest. Откройте pinterest.com в этом браузере.")
                self.driver.quit()
                self.driver = None
                return False
            self.connected = True
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к браузеру: {e}")
            return False

    def _download_image(self, url):
        url_hash = hashlib.md5(url.encode()).hexdigest()
        local_path = os.path.join(IMAGES_DIR, f"{url_hash}.jpg")
        if os.path.exists(local_path):
            return local_path

        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, timeout=10, headers=headers)
            if resp.status_code == 200:
                img_array = np.frombuffer(resp.content, np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img is not None:
                    cv2.imwrite(local_path, img)
                    return local_path
        except:
            pass
        return None

    def _collection_loop(self, category, label, target_count, search_term):
        self.status['collected'] = 0
        self.status['target'] = target_count if target_count > 0 else 0
        self.status['scrolls'] = 0
        self.status['category'] = category
        self.status['search_term'] = search_term or ''
        self.status['infinite'] = (target_count == 0)
        self.status['active'] = True

        actual_target = target_count if target_count > 0 else 999999

        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            if "pinterest.com" in self.driver.current_url:
                break

        time.sleep(2)
        try:
            search_input = self.driver.find_element(By.CSS_SELECTOR, "input[data-test-id='search-box-input']")
            search_input.clear()
            search_input.send_keys(search_term)
            time.sleep(1)
            search_input.send_keys(Keys.RETURN)
            time.sleep(5)
        except:
            pass

        processed_urls = set()
        while self.is_running and self.status['collected'] < actual_target:
            self.driver.execute_script("window.scrollBy(0, 800);")
            self.status['scrolls'] += 1
            for _ in range(int(SCROLL_DELAY * 10)):
                if not self.is_running:
                    break
                time.sleep(0.1)
            if not self.is_running:
                break

            imgs = self.driver.find_elements(By.TAG_NAME, "img")
            for img in imgs:
                if not self.is_running:
                    break
                try:
                    src = img.get_attribute("src")
                    if not src or src in processed_urls:
                        continue
                    if '75x75' in src or '100x100' in src or 'avatar' in src:
                        continue
                    clean_src = src.split('?')[0]
                    processed_urls.add(clean_src)

                    if self.dm.is_duplicate(clean_src):
                        continue

                    local_path = self._download_image(clean_src)
                    if local_path:
                        self.dm.add_pending({
                            'img_url': clean_src,
                            'local_path': local_path,
                            'category': category,
                            'source': 'pinterest',
                            'search_term': search_term
                        })
                        self.status['collected'] += 1
                    else:
                        self.dm.add_rejected(clean_src)

                    if self.status['collected'] >= actual_target:
                        break
                    time.sleep(0.2)
                except:
                    continue

        self.status['active'] = False
        self.is_running = False
        print(f"Сбор завершён. Собрано {self.status['collected']} изображений")

    def start_collection(self, category, target_count, search_term=None):
        if self.is_running:
            return False, "Сбор уже идёт"

        if not self.connect():
            return False, "Браузер не подключён. Запустите Chrome с --remote-debugging-port=9222 и откройте Pinterest"

        label = 1 if category == 'alt_girls' else 0
        if not search_term:
            import random
            terms = {
                'alt_girls': ['alt girl aesthetic', 'alternative fashion', 'goth girl', 'punk style'],
                'not_alt': ['landscape nature', 'food photography', 'architecture', 'cute animals']
            }
            search_term = random.choice(terms.get(category, ['cat']))

        self.is_running = True
        self.thread = threading.Thread(
            target=self._collection_loop,
            args=(category, label, target_count, search_term),
            daemon=True
        )
        self.thread.start()
        return True, f"Сбор запущен: {search_term}"

    def stop_collection(self):
        self.is_running = False
        self.status['active'] = False
        return True, "Сбор остановлен"

    def get_status(self):
        return {
            'is_running': self.is_running,
            'collected': self.status['collected'],
            'target': self.status['target'],
            'scrolls': self.status['scrolls'],
            'infinite': self.status['infinite'],
            'category': self.status['category'],
            'search_term': self.status['search_term']
        }
