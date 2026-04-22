from flask import Blueprint, render_template, jsonify, request, send_file
import os
from core.data_manager import DataManager
from core.collector import PinterestCollector
from core.model import ModelManager
from core.liker import AltLiker
from config import IMAGES_DIR

web_bp = Blueprint('web', __name__)

dm = DataManager()
collector = PinterestCollector(dm)
model_mgr = ModelManager()
liker = AltLiker()

@web_bp.route('/')
def index():
    return render_template('index.html')

@web_bp.route('/api/images/<status>')
def api_images(status):
    if status == 'pending':
        data = dm.get_pending()
    elif status == 'labeled':
        data = dm.get_labeled()
    elif status == 'rejected':
        data = dm.get_rejected_list()
    else:
        return jsonify([]), 404
    return jsonify(data)

@web_bp.route('/api/label', methods=['POST'])
def api_label():
    data = request.json
    img_url = data['img_url']
    label = int(data['label'])
    success = dm.label_image(img_url, label)
    return jsonify({'status': 'ok' if success else 'error'})

@web_bp.route('/api/skip', methods=['POST'])
def api_skip():
    data = request.json
    img_url = data['img_url']
    dm.skip_image(img_url)
    return jsonify({'status': 'ok'})

@web_bp.route('/api/collect/start', methods=['POST'])
def api_collect_start():
    data = request.json
    category = data.get('category', 'alt_girls')
    count = data.get('count', 0)
    search_term = data.get('search_term', '')
    success, message = collector.start_collection(category, count, search_term)
    return jsonify({'success': success, 'message': message})

@web_bp.route('/api/collect/stop', methods=['POST'])
def api_collect_stop():
    success, message = collector.stop_collection()
    return jsonify({'success': success, 'message': message})

@web_bp.route('/api/collect/status')
def api_collect_status():
    status = collector.get_status()
    stats = dm.get_statistics()
    status.update(stats)
    return jsonify(status)

@web_bp.route('/api/train', methods=['POST'])
def api_train():
    images, labels = dm.get_all_images_for_training()
    success, message = model_mgr.train(images, labels)
    return jsonify({'success': success, 'message': message})

@web_bp.route('/api/model/status')
def api_model_status():
    return jsonify({'trained': model_mgr.is_trained()})

@web_bp.route('/api/liker/start', methods=['POST'])
def api_liker_start():
    success, message = liker.start()
    return jsonify({'success': success, 'message': message})

@web_bp.route('/api/liker/stop', methods=['POST'])
def api_liker_stop():
    success, message = liker.stop()
    return jsonify({'success': success, 'message': message})

@web_bp.route('/api/liker/status')
def api_liker_status():
    return jsonify(liker.get_status())

@web_bp.route('/api/liker/liked')
def api_liker_liked():
    return jsonify({'images': liker.get_liked_images()})

@web_bp.route('/api/liker/test', methods=['POST'])
def api_liker_test():
    if 'image' in request.files:
        file = request.files['image']
        temp_path = os.path.join(IMAGES_DIR, 'temp_test.jpg')
        file.save(temp_path)
        result = liker.test_image(temp_path)
        os.remove(temp_path)
        return jsonify(result)
    elif request.json and 'url' in request.json:
        url = request.json['url']
        result = liker.test_url(url)
        return jsonify(result)
    return jsonify({'error': 'No image provided'}), 400

@web_bp.route('/image/<path:filename>')
def serve_image(filename):
    return send_file(os.path.join(IMAGES_DIR, filename))

@web_bp.route('/liked_image/<img_id>')
def serve_liked_image(img_id):
    for img in liker.liked_images:
        if img['id'] == img_id and os.path.exists(img['local_path']):
            return send_file(img['local_path'], mimetype='image/jpeg')
    return "Not found", 404
