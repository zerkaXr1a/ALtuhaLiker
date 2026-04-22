import time
import threading
import requests
import numpy as np
import cv2
import os
import hashlib
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException
from config import CHROME_DEBUG_PORT, IMAGES_DIR
from core.model import ModelManager

class AltLiker:
    def __init__(self):
        self.driver = None
        self.connected = False
        self.is_running = False
        self.thread = None
        self.stats = {
            'processed': 0,
            'liked': 0,
            'scrolls': 0,
            'failed_likes': 0
        }
        self.liked_images = []
        self.model_mgr = ModelManager()
        self.threshold = 0.44

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
                if "xn--d1ah4a.com" in self.driver.current_url:
                    found = True
                    break
            if not found:
                print("❌ Не найдена вкладка ИТД. Откройте xn--d1ah4a.com в этом браузере.")
                self.driver.quit()
                self.driver = None
                return False
            self.connected = True
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False

    def _get_image_from_url(self, url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, timeout=5, headers=headers)
            if resp.status_code == 200:
                img_array = np.frombuffer(resp.content, np.uint8)
                return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        except:
            pass
        return None

    def _save_liked_image(self, img_url, prob):
        url_hash = hashlib.md5(img_url.encode()).hexdigest()
        local_path = os.path.join(IMAGES_DIR, f"liked_{url_hash}.jpg")
        img_data = self._get_image_from_url(img_url)
        if img_data is not None:
            cv2.imwrite(local_path, img_data)

        self.liked_images.insert(0, {
            'id': url_hash,
            'url': img_url,
            'local_path': local_path,
            'probability': float(prob),
            'timestamp': datetime.now().isoformat(),
            'percentage': f"{prob*100:.1f}%"
        })
        if len(self.liked_images) > 100:
            removed = self.liked_images.pop()
            if os.path.exists(removed['local_path']):
                try:
                    os.remove(removed['local_path'])
                except:
                    pass

    def _get_post_articles(self):
        return self.driver.find_elements(By.CSS_SELECTOR, 'div.WLz2 article.b4uQ')

    def _find_image_in_article(self, article):
        try:
            imgs = article.find_elements(By.TAG_NAME, "img")
            for img in imgs:
                try:
                    w = int(img.get_attribute("width") or 0)
                    h = int(img.get_attribute("height") or 0)
                    if w >= 100 and h >= 100:
                        return img
                except StaleElementReferenceException:
                    continue
        except StaleElementReferenceException:
            pass
        return None

    def _bot_loop(self):
        self.stats = {'processed': 0, 'liked': 0, 'scrolls': 0, 'failed_likes': 0}
        processed_urls = set()

        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            if "xn--d1ah4a.com" in self.driver.current_url:
                break

        print("🤖 Бот запущен. Обхожу посты по одному...")
        last_article_count = 0
        current_index = 0

        while self.is_running:
            try:
                articles = self._get_post_articles()
                if not articles:
                    time.sleep(1)
                    continue

                if current_index >= len(articles):
                    self.driver.execute_script("window.scrollBy(0, 800);")
                    self.stats['scrolls'] += 1
                    time.sleep(2)
                    current_index = 0
                    continue

                article = articles[current_index]

                img = self._find_image_in_article(article)
                if not img:
                    current_index += 1
                    continue

                src = img.get_attribute("src")
                if not src or not src.startswith("http"):
                    current_index += 1
                    continue

                if src in processed_urls:
                    current_index += 1
                    continue

                processed_urls.add(src)
                self.stats['processed'] += 1

                img_data = self._get_image_from_url(src)
                if img_data is None:
                    current_index += 1
                    continue

                temp_path = os.path.join(IMAGES_DIR, "temp_liker.jpg")
                cv2.imwrite(temp_path, img_data)
                result = self.model_mgr.predict(temp_path)
                os.remove(temp_path)

                if 'error' not in result:
                    prob = result.get('probability', 0.5)
                    if prob > self.threshold:
                        try:
                            fresh_articles = self._get_post_articles()
                            if current_index < len(fresh_articles):
                                fresh_article = fresh_articles[current_index]
                                like_btn = fresh_article.find_element(By.CSS_SELECTOR, 'button[aria-label="Нравится"].oafD')
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", like_btn)
                                time.sleep(0.3)

                                classes_before = like_btn.get_attribute("class") or ""
                                if "FLFz" not in classes_before:
                                    actions = ActionChains(self.driver)
                                    actions.move_to_element(like_btn).pause(0.2).click().perform()
                                    time.sleep(0.7)

                                    classes_after = like_btn.get_attribute("class") or ""
                                    if "FLFz" in classes_after:
                                        self.stats['liked'] += 1
                                        self._save_liked_image(src, prob)
                                        print(f"❤️ Лайк #{self.stats['liked']}! ({result.get('percentage', '?%')})")
                                    else:
                                        self.stats['failed_likes'] += 1
                                        print(f"⚠️ Не удалось активировать лайк (класс FLFz не появился)")
                        except Exception as e:
                            self.stats['failed_likes'] += 1
                            print(f"⚠️ Не удалось поставить лайк: {e}")

                current_index += 1

                if self.stats['processed'] % 5 == 0:
                    print(f"📊 Обработано постов: {self.stats['processed']} | Лайков: {self.stats['liked']}")

            except StaleElementReferenceException:
                time.sleep(0.5)
                continue
            except Exception as e:
                print(f"⚠️ Неожиданная ошибка в цикле: {e}")
                time.sleep(1)

        print(f"⏹️ Бот остановлен. Итого: скроллов {self.stats['scrolls']}, лайков {self.stats['liked']}")

    def start(self):
        if self.is_running:
            return False, "Бот уже запущен"
        if not self.connect():
            return False, "Не удалось подключиться к браузеру с ИТД"
        if not self.model_mgr.is_trained():
            return False, "Модель не обучена. Сначала обучите модель."

        self.is_running = True
        self.thread = threading.Thread(target=self._bot_loop, daemon=True)
        self.thread.start()
        return True, "Бот запущен"

    def stop(self):
        self.is_running = False
        return True, "Бот остановлен"

    def get_status(self):
        return {
            'is_running': self.is_running,
            'processed': int(self.stats['processed']),
            'liked': int(self.stats['liked']),
            'scrolls': int(self.stats['scrolls']),
            'failed_likes': int(self.stats['failed_likes']),
            'threshold': float(self.threshold),
            'model_trained': self.model_mgr.is_trained()
        }

    def get_liked_images(self, limit=50):
        return self.liked_images[:limit]

    def test_image(self, image_path):
        result = self.model_mgr.predict(image_path)
        return result

    def test_url(self, url):
        img_data = self._get_image_from_url(url)
        if img_data is None:
            return {'error': 'Не удалось загрузить изображение'}
        temp_path = os.path.join(IMAGES_DIR, "temp_test.jpg")
        cv2.imwrite(temp_path, img_data)
        result = self.model_mgr.predict(temp_path)
        os.remove(temp_path)
        return result
