import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, 'data')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')
MODEL_DIR = os.path.join(DATA_DIR, 'model')

DATASET_FILE = os.path.join(DATA_DIR, 'dataset.json')
PENDING_FILE = os.path.join(DATA_DIR, 'pending.json')
REJECTED_FILE = os.path.join(DATA_DIR, 'rejected.json')
MODEL_FILE = os.path.join(MODEL_DIR, 'alt_brain.pkl')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

CHROME_DEBUG_PORT = 9222
DEFAULT_TARGET_COUNT = 30
SCROLL_DELAY = 1.5

INVERT_MODEL_LABELS = False   # если метки перепутаны (альтуха=0), поставь True
