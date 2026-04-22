import json
import os
import shutil
from config import DATASET_FILE, PENDING_FILE, REJECTED_FILE, IMAGES_DIR

class DataManager:
    def __init__(self):
        self.dataset = []
        self.pending = []
        self.rejected = set()
        self.load()

    def load(self):
        if os.path.exists(DATASET_FILE):
            with open(DATASET_FILE, 'r', encoding='utf-8') as f:
                self.dataset = json.load(f)
        if os.path.exists(PENDING_FILE):
            with open(PENDING_FILE, 'r', encoding='utf-8') as f:
                self.pending = json.load(f)
        if os.path.exists(REJECTED_FILE):
            with open(REJECTED_FILE, 'r', encoding='utf-8') as f:
                self.rejected = set(json.load(f))
        else:
            self.rejected = set()

    def save(self):
        with open(DATASET_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.dataset, f, indent=2, ensure_ascii=False)
        with open(PENDING_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.pending, f, indent=2, ensure_ascii=False)
        with open(REJECTED_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(self.rejected), f, indent=2, ensure_ascii=False)

    def is_duplicate(self, img_url):
        for item in self.dataset:
            if item['img_url'] == img_url:
                return True
        for item in self.pending:
            if item['img_url'] == img_url:
                return True
        return img_url in self.rejected

    def add_pending(self, image_info):
        self.pending.append(image_info)
        self.save()

    def add_rejected(self, img_url):
        self.rejected.add(img_url)
        self.save()

    def get_pending(self):
        labeled_urls = {item['img_url'] for item in self.dataset}
        return [img for img in self.pending if img['img_url'] not in labeled_urls and img['img_url'] not in self.rejected]

    def get_labeled(self):
        return self.dataset

    def get_rejected_list(self):
        return [{'img_url': url, 'status': 'rejected'} for url in self.rejected]

    def label_image(self, img_url, label):
        for img in self.pending:
            if img['img_url'] == img_url:
                self.dataset.append({
                    'img_url': img_url,
                    'label': label,
                    'category': img.get('category', 'unknown'),
                    'source': img.get('source', 'pinterest'),
                    'local_path': img['local_path']
                })
                self.pending.remove(img)
                self.save()
                return True
        return False

    def skip_image(self, img_url):
        self.rejected.add(img_url)
        self.pending = [img for img in self.pending if img['img_url'] != img_url]
        self.save()
        return True

    def get_statistics(self):
        alt_count = sum(1 for item in self.dataset if item['label'] == 1)
        not_count = len(self.dataset) - alt_count
        return {
            'total_labeled': len(self.dataset),
            'alt_count': alt_count,
            'not_count': not_count,
            'pending': len(self.get_pending()),
            'rejected': len(self.rejected)
        }

    def get_all_images_for_training(self):
        images = []
        labels = []
        for item in self.dataset:
            path = item.get('local_path')
            if path and os.path.exists(path):
                images.append(path)
                labels.append(item['label'])
        return images, labels
