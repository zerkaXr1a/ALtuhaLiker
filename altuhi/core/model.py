import os
import cv2
from config import MODEL_FILE
from brain import ImprovedBrain

class ModelManager:
    def __init__(self):
        self.brain = ImprovedBrain()
        self.load()

    def load(self):
        if os.path.exists(MODEL_FILE):
            self.brain.load(MODEL_FILE)
        else:
            print("Модель не найдена. Обучите модель.")

    def is_trained(self):
        return self.brain.is_trained

    def train(self, image_paths, labels):
        if len(image_paths) < 10:
            return False, f"Недостаточно данных: {len(image_paths)} (минимум 10)"

        unique_labels = set(labels)
        if len(unique_labels) < 2:
            return False, "Нужны примеры обоих классов (Альтуха и Не альтуха)"

        valid_paths = []
        valid_labels = []
        for path, label in zip(image_paths, labels):
            if os.path.exists(path):
                img = cv2.imread(path)
                if img is not None:
                    valid_paths.append(path)
                    valid_labels.append(label)

        if len(valid_paths) < 10:
            return False, f"Недостаточно валидных изображений: {len(valid_paths)}"

        if len(set(valid_labels)) < 2:
            return False, "После фильтрации остался только один класс"

        accuracy = self.brain.train(valid_paths, valid_labels, verbose=True)
        self.brain.save(MODEL_FILE)
        return True, f"Обучено на {len(valid_paths)} фото, точность {accuracy:.1%}"

    def predict(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            return {'error': 'Не удалось загрузить изображение'}
        if not self.is_trained():
            return {'verdict': 'Модель не обучена', 'probability': 0.5, 'percentage': '50%', 'confidence': 'low'}
        return self.brain.predict_with_details(img)
