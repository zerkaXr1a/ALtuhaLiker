import os
import pickle
import numpy as np
import cv2
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from torch.utils.data import Dataset, DataLoader
from config import MODEL_FILE, INVERT_MODEL_LABELS

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class ImagePathDataset(Dataset):
    def __init__(self, image_paths, labels, transform, invert_labels=False):
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform
        self.invert_labels = invert_labels

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        path = self.image_paths[idx]
        label = self.labels[idx]
        if self.invert_labels:
            label = 1 - label
        img = cv2.imread(path)
        if img is None:
            img = np.zeros((224, 224, 3), dtype=np.uint8)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        tensor = self.transform(img)
        return tensor, torch.tensor(label, dtype=torch.float32)

class ImprovedBrain:
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.version = "4.0_cnn_mobilenetv2"
        self._build_model()
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
        ])

    def _build_model(self):
        self.model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
        for param in self.model.parameters():
            param.requires_grad = False
        in_features = self.model.classifier[1].in_features
        self.model.classifier[1] = nn.Linear(in_features, 1)
        self.model.to(device)
        self.model.eval()

    def _preprocess(self, img_bgr):
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        return self.transform(img_rgb).unsqueeze(0).to(device)

    def predict(self, img):
        if not self.is_trained:
            return 0.5
        self.model.eval()
        with torch.no_grad():
            tensor = self._preprocess(img)
            output = self.model(tensor)
            prob = torch.sigmoid(output).item()
        return prob

    def predict_with_details(self, img):
        prob = self.predict(img)
        if prob > 0.7 or prob < 0.3:
            confidence = 'high'
        elif prob > 0.6 or prob < 0.4:
            confidence = 'medium'
        else:
            confidence = 'low'
        should_like = prob > 0.44
        return {
            'probability': prob,
            'percentage': f"{prob*100:.1f}%",
            'verdict': 'АЛЬТУХА' if prob > 0.5 else 'НЕ АЛЬТУХА',
            'verdict_en': 'alt' if prob > 0.5 else 'not_alt',
            'confidence': confidence,
            'should_like': should_like
        }

    def train(self, image_paths, labels, verbose=True):
        if len(image_paths) < 10:
            if verbose:
                print("❌ Недостаточно данных (минимум 10)")
            return 0.0

        dataset = ImagePathDataset(
            image_paths, labels, self.transform,
            invert_labels=INVERT_MODEL_LABELS
        )
        dataloader = DataLoader(dataset, batch_size=8, shuffle=True, num_workers=0)

        for param in self.model.classifier.parameters():
            param.requires_grad = True

        optimizer = torch.optim.Adam(self.model.classifier.parameters(), lr=0.001)
        criterion = nn.BCEWithLogitsLoss()

        self.model.train()
        epochs = 5
        for epoch in range(epochs):
            total_loss = 0.0
            correct = 0
            total = 0
            for batch_X, batch_y in dataloader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                optimizer.zero_grad()
                outputs = self.model(batch_X).squeeze()
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

                total_loss += loss.item()
                preds = (torch.sigmoid(outputs) > 0.5).float()
                correct += (preds == batch_y).sum().item()
                total += batch_y.size(0)

            acc = correct / total if total > 0 else 0.0
            if verbose:
                print(f"   Epoch {epoch+1}/{epochs} - loss: {total_loss/len(dataloader):.4f} - acc: {acc:.3f}")

        self.model.eval()
        self.is_trained = True

        correct_total = 0
        total_total = 0
        with torch.no_grad():
            for batch_X, batch_y in dataloader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                outputs = self.model(batch_X).squeeze()
                preds = (torch.sigmoid(outputs) > 0.5).float()
                correct_total += (preds == batch_y).sum().item()
                total_total += batch_y.size(0)
        accuracy = correct_total / total_total if total_total > 0 else 0.0

        if verbose:
            print(f"✅ Обучение завершено. Точность: {accuracy:.1%}")
        return accuracy

    def save(self, path=MODEL_FILE):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        state = {
            'model_state': self.model.state_dict(),
            'is_trained': self.is_trained,
            'version': self.version
        }
        with open(path, 'wb') as f:
            pickle.dump(state, f)

    def load(self, path=MODEL_FILE):
        if not os.path.exists(path):
            print(f"⚠️ Файл модели {path} не найден.")
            return False
        try:
            with open(path, 'rb') as f:
                state = pickle.load(f)
            if 'model_state' in state:
                self.model.load_state_dict(state['model_state'])
                self.is_trained = state.get('is_trained', True)
                self.version = state.get('version', 'unknown')
            else:
                print("⚠️ Старая модель sklearn. Требуется переобучение.")
                self.is_trained = False
                return False
            self.model.to(device)
            self.model.eval()
            print(f"✅ CNN модель загружена из {path} (v{self.version})")
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
            return False
