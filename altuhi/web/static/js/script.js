document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('imageGrid');
    const emptyState = document.getElementById('emptyState');
    const pageTitle = document.getElementById('pageTitle');
    const navBtns = document.querySelectorAll('.nav-btn');
    const refreshBtn = document.getElementById('refreshBtn');
    const collectBtn = document.getElementById('collectBtn');
    const trainBtn = document.getElementById('trainBtn');
    const notificationArea = document.getElementById('notificationArea');

    const likerPanel = document.getElementById('likerPanel');

    const previewModal = document.getElementById('previewModal');
    const previewImage = document.getElementById('previewImage');
    const previewSource = document.getElementById('previewSource');
    const previewActions = document.getElementById('previewActions');
    const collectModal = document.getElementById('collectModal');

    const collectCategory = document.getElementById('collectCategory');
    const collectSearch = document.getElementById('collectSearch');
    const collectCount = document.getElementById('collectCount');
    const collectStartBtn = document.getElementById('collectStartBtn');
    const collectStopBtn = document.getElementById('collectStopBtn');
    const collectProgress = document.getElementById('collectProgress');

    const likerStartBtn = document.getElementById('likerStartBtn');
    const likerStopBtn = document.getElementById('likerStopBtn');
    const likerStatusText = document.getElementById('likerStatusText');
    const likerScrolls = document.getElementById('likerScrolls');
    const likerProcessed = document.getElementById('likerProcessed');
    const likerLiked = document.getElementById('likerLiked');
    const likerFailed = document.getElementById('likerFailed');
    const likerThreshold = document.getElementById('likerThreshold');
    const likedGrid = document.getElementById('likedGrid');
    const likerStatusBadge = document.getElementById('likerStatusBadge');

    const testImageInput = document.getElementById('testImageInput');
    const testImageUrl = document.getElementById('testImageUrl');
    const testUrlBtn = document.getElementById('testUrlBtn');
    const testPreviewImg = document.getElementById('testPreviewImg');
    const testResult = document.getElementById('testResult');

    let currentTab = 'pending';
    let currentImages = [];
    let collectInterval = null;
    let likerInterval = null;

    const pendingCountEl = document.getElementById('pendingCount');
    const labeledCountEl = document.getElementById('labeledCount');
    const rejectedCountEl = document.getElementById('rejectedCount');

    function init() {
        loadTab(currentTab);
        loadCounts();
        attachEvents();
        checkCollectionStatus();
    }

    function attachEvents() {
        navBtns.forEach(btn => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));
        refreshBtn.addEventListener('click', () => loadTab(currentTab));
        collectBtn.addEventListener('click', openCollectModal);
        trainBtn.addEventListener('click', trainModel);

        if (likerStartBtn) likerStartBtn.addEventListener('click', startLiker);
        if (likerStopBtn) likerStopBtn.addEventListener('click', stopLiker);
        if (testUrlBtn) testUrlBtn.addEventListener('click', testByUrl);
        if (testImageInput) testImageInput.addEventListener('change', testByFile);

        document.querySelectorAll('.modal-close').forEach(btn => btn.addEventListener('click', closeAllModals));
        document.querySelectorAll('.modal-overlay').forEach(overlay => overlay.addEventListener('click', closeAllModals));
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeAllModals();
        });

        collectStartBtn.addEventListener('click', startCollection);
        collectStopBtn.addEventListener('click', stopCollection);
    }

    function switchTab(tab) {
        currentTab = tab;
        navBtns.forEach(btn => btn.classList.toggle('active', btn.dataset.tab === tab));

        if (tab === 'liker') {
            grid.style.display = 'none';
            emptyState.style.display = 'none';
            likerPanel.style.display = 'block';
            pageTitle.textContent = 'Лайкер альтух';
            updateLikerStatus();
            loadLikedImages();
            startLikerStatusPolling();
        } else {
            likerPanel.style.display = 'none';
            stopLikerStatusPolling();
            pageTitle.textContent = tab === 'pending' ? 'Очередь на разметку' :
                                   tab === 'labeled' ? 'Размеченные изображения' : 'Отклонённые изображения';
            loadTab(tab);
        }
    }

    async function loadTab(tab) {
        try {
            const res = await fetch(`/api/images/${tab}`);
            const data = await res.json();
            currentImages = data;
            renderGrid(data, tab);
            updateCounts();
        } catch (err) {
            showNotification('Ошибка загрузки данных', 'error');
        }
    }

    async function loadCounts() {
        try {
            const [pending, labeled, rejected] = await Promise.all([
                fetch('/api/images/pending').then(r => r.json()),
                fetch('/api/images/labeled').then(r => r.json()),
                fetch('/api/images/rejected').then(r => r.json())
            ]);
            pendingCountEl.textContent = pending.length;
            labeledCountEl.textContent = labeled.length;
            rejectedCountEl.textContent = rejected.length;
        } catch (err) {
            console.error('Ошибка счётчиков', err);
        }
    }

    function updateCounts() {
        loadCounts();
    }

    function renderGrid(images, tab) {
        if (!images || images.length === 0) {
            grid.style.display = 'none';
            emptyState.style.display = 'flex';
            return;
        }
        grid.style.display = 'grid';
        emptyState.style.display = 'none';

        let html = '';
        images.forEach((img, idx) => {
            const imageUrl = `/image/${img.local_path ? img.local_path.split(/[\\/]/).pop() : img.img_url.split('/').pop()}`;
            const isPending = tab === 'pending';
            const labelText = img.label === 1 ? 'Альтуха' : (img.label === 0 ? 'Не альтуха' : '');
            const statusClass = img.label === 1 ? 'status-posted' : (img.label === 0 ? 'status-rejected' : 'status-pending');

            let actions = '';
            if (isPending) {
                actions = `
                    <div class="card-actions">
                        <button class="approve-btn" data-url="${img.img_url}" data-action="label" data-label="1" title="Альтуха">
                            <i class="fas fa-check"></i>
                        </button>
                        <button class="reject-btn" data-url="${img.img_url}" data-action="label" data-label="0" title="Не альтуха">
                            <i class="fas fa-times"></i>
                        </button>
                        <button class="skip-btn" data-url="${img.img_url}" data-action="skip" title="Пропустить">
                            <i class="fas fa-forward"></i>
                        </button>
                    </div>
                `;
            }

            html += `
                <div class="meme-card" data-url="${img.img_url}" data-index="${idx}">
                    <img src="${imageUrl}" alt="Фото" class="card-image" loading="lazy">
                    <div class="card-content">
                        <div class="card-source">${img.category || 'pinterest'}</div>
                        <div class="card-description">${img.search_term || ''}</div>
                        <div class="card-footer">
                            <span class="status-badge ${statusClass}">${labelText || (isPending ? 'pending' : 'rejected')}</span>
                            ${actions}
                        </div>
                    </div>
                </div>
            `;
        });
        grid.innerHTML = html;

        document.querySelectorAll('.meme-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (e.target.closest('button')) return;
                const url = card.dataset.url;
                const imgData = currentImages.find(i => i.img_url === url);
                openPreview(imgData);
            });
        });

        document.querySelectorAll('[data-action="label"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const url = btn.dataset.url;
                const label = parseInt(btn.dataset.label);
                labelImage(url, label);
            });
        });

        document.querySelectorAll('[data-action="skip"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                skipImage(btn.dataset.url);
            });
        });
    }

    async function labelImage(url, label) {
        try {
            await fetch('/api/label', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({img_url: url, label: label})
            });
            showNotification(`Отмечено как ${label === 1 ? 'Альтуха' : 'Не альтуха'}`, 'success');
            loadTab(currentTab);
        } catch (err) {
            showNotification('Ошибка при разметке', 'error');
        }
    }

    async function skipImage(url) {
        try {
            await fetch('/api/skip', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({img_url: url})
            });
            showNotification('Пропущено', 'info');
            loadTab(currentTab);
        } catch (err) {
            showNotification('Ошибка', 'error');
        }
    }

    function openPreview(imgData) {
        if (!imgData) return;
        const imageUrl = `/image/${imgData.local_path ? imgData.local_path.split(/[\\/]/).pop() : imgData.img_url.split('/').pop()}`;
        previewImage.src = imageUrl;
        previewSource.textContent = `Источник: ${imgData.category || 'pinterest'} · ${imgData.search_term || ''}`;

        if (currentTab === 'pending') {
            previewActions.innerHTML = `
                <button class="btn-primary" id="modalApprove" style="background: var(--success);">
                    <i class="fas fa-check"></i> Альтуха
                </button>
                <button class="btn-secondary" id="modalReject">
                    <i class="fas fa-times"></i> Не альтуха
                </button>
                <button class="btn-secondary" id="modalSkip">
                    <i class="fas fa-forward"></i> Пропустить
                </button>
            `;
            document.getElementById('modalApprove').addEventListener('click', () => {
                labelImage(imgData.img_url, 1);
                closeAllModals();
            });
            document.getElementById('modalReject').addEventListener('click', () => {
                labelImage(imgData.img_url, 0);
                closeAllModals();
            });
            document.getElementById('modalSkip').addEventListener('click', () => {
                skipImage(imgData.img_url);
                closeAllModals();
            });
        } else {
            const labelText = imgData.label === 1 ? 'Альтуха' : 'Не альтуха';
            previewActions.innerHTML = `<span class="status-badge ${imgData.label === 1 ? 'status-posted' : 'status-rejected'}">${labelText}</span>`;
        }

        previewModal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeAllModals() {
        previewModal.classList.remove('active');
        collectModal.classList.remove('active');
        document.body.style.overflow = '';
    }

    function openCollectModal() {
        collectModal.classList.add('active');
        document.body.style.overflow = 'hidden';
        updateCollectUI();
    }

    async function startCollection() {
        const category = collectCategory.value;
        const searchTerm = collectSearch.value.trim();
        const count = parseInt(collectCount.value) || 0;

        try {
            const res = await fetch('/api/collect/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({category, count, search_term: searchTerm})
            });
            const data = await res.json();
            if (data.success) {
                showNotification(data.message, 'success');
                collectStartBtn.style.display = 'none';
                collectStopBtn.style.display = 'inline-block';
                startCollectStatusPolling();
            } else {
                showNotification(data.message, 'error');
            }
        } catch (err) {
            showNotification('Ошибка запуска сбора', 'error');
        }
    }

    async function stopCollection() {
        try {
            await fetch('/api/collect/stop', {method: 'POST'});
            showNotification('Сбор остановлен', 'info');
            collectStartBtn.style.display = 'inline-block';
            collectStopBtn.style.display = 'none';
            stopCollectStatusPolling();
        } catch (err) {
            showNotification('Ошибка', 'error');
        }
    }

    function startCollectStatusPolling() {
        if (collectInterval) clearInterval(collectInterval);
        collectInterval = setInterval(checkCollectionStatus, 2000);
    }

    function stopCollectStatusPolling() {
        if (collectInterval) {
            clearInterval(collectInterval);
            collectInterval = null;
        }
    }

    async function checkCollectionStatus() {
        try {
            const res = await fetch('/api/collect/status');
            const data = await res.json();
            updateCollectUI(data);
            if (!data.is_running) {
                collectStartBtn.style.display = 'inline-block';
                collectStopBtn.style.display = 'none';
                stopCollectStatusPolling();
                if (currentTab !== 'liker') loadTab(currentTab);
            }
            const statusDiv = document.getElementById('collectStatus');
            if (data.is_running) {
                let text = `Сбор: ${data.collected}`;
                if (!data.infinite && data.target > 0) text += `/${data.target}`;
                text += ` | Скроллы: ${data.scrolls}`;
                statusDiv.textContent = text;
                statusDiv.classList.add('active');
            } else {
                statusDiv.textContent = '';
                statusDiv.classList.remove('active');
            }
        } catch (err) {
            console.error('Ошибка статуса', err);
        }
    }

    function updateCollectUI(status) {
        if (!status) return;
        const progressDiv = collectProgress;
        if (status.is_running) {
            let progressText = `Собрано: ${status.collected}`;
            if (!status.infinite && status.target > 0) {
                const percent = (status.collected / status.target) * 100;
                progressText += ` / ${status.target} (${percent.toFixed(0)}%)`;
            }
            progressText += ` | Скроллы: ${status.scrolls}`;
            progressDiv.innerHTML = `<div class="progress-bar"><div class="progress-fill" style="width:${status.infinite ? 100 : (status.collected/status.target)*100}%"></div></div><div>${progressText}</div>`;
        } else {
            progressDiv.innerHTML = '';
        }
    }

    async function trainModel() {
        try {
            trainBtn.disabled = true;
            trainBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Обучение...';
            const res = await fetch('/api/train', {method: 'POST'});
            const data = await res.json();
            if (data.success) {
                showNotification(data.message, 'success');
            } else {
                showNotification(data.message, 'error');
            }
        } catch (err) {
            showNotification('Ошибка обучения', 'error');
        } finally {
            trainBtn.disabled = false;
            trainBtn.innerHTML = '<i class="fas fa-brain"></i> Обучить модель';
        }
    }

    async function startLiker() {
        const res = await fetch('/api/liker/start', {method: 'POST'});
        const data = await res.json();
        showNotification(data.message, data.success ? 'success' : 'error');
        updateLikerStatus();
    }

    async function stopLiker() {
        const res = await fetch('/api/liker/stop', {method: 'POST'});
        const data = await res.json();
        showNotification(data.message, 'info');
        updateLikerStatus();
    }

    async function updateLikerStatus() {
        try {
            const res = await fetch('/api/liker/status');
            const data = await res.json();
            likerScrolls.textContent = data.scrolls || 0;
            likerProcessed.textContent = data.processed || 0;
            likerLiked.textContent = data.liked || 0;
            likerFailed.textContent = data.failed_likes || 0;
            likerThreshold.textContent = data.threshold;

            if (data.is_running) {
                likerStatusText.innerHTML = '🟢 Бот работает';
                likerStatusText.className = 'status-running';
                likerStatusBadge.textContent = '🟢';
                likerStatusBadge.style.background = '#2ed573';
            } else {
                likerStatusText.innerHTML = '⚪ Бот остановлен';
                likerStatusText.className = 'status-stopped';
                likerStatusBadge.textContent = '⚪';
                likerStatusBadge.style.background = '';
            }
        } catch (err) {
            console.error('Ошибка статуса лайкера', err);
        }
    }

    async function loadLikedImages() {
        try {
            const res = await fetch('/api/liker/liked');
            const data = await res.json();
            const images = data.images || [];
            if (images.length === 0) {
                likedGrid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px;">Пока нет лайкнутых фото</div>';
                return;
            }
            let html = '';
            images.forEach(img => {
                html += `
                    <div class="meme-card">
                        <img src="/liked_image/${img.id}" alt="Liked" class="card-image" loading="lazy">
                        <div class="card-content">
                            <div class="card-source">${img.percentage}</div>
                            <div class="card-description">${new Date(img.timestamp).toLocaleString()}</div>
                        </div>
                    </div>
                `;
            });
            likedGrid.innerHTML = html;
        } catch (err) {
            console.error('Ошибка загрузки лайкнутых', err);
        }
    }

    function startLikerStatusPolling() {
        if (likerInterval) clearInterval(likerInterval);
        likerInterval = setInterval(() => {
            updateLikerStatus();
            loadLikedImages();
        }, 3000);
    }

    function stopLikerStatusPolling() {
        if (likerInterval) {
            clearInterval(likerInterval);
            likerInterval = null;
        }
    }

    async function testByFile() {
        const file = testImageInput.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('image', file);
        testPreviewImg.src = URL.createObjectURL(file);
        testPreviewImg.style.display = 'block';
        testResult.innerHTML = 'Анализ...';
        const res = await fetch('/api/liker/test', {method: 'POST', body: formData});
        const data = await res.json();
        displayTestResult(data);
    }

    async function testByUrl() {
        const url = testImageUrl.value.trim();
        if (!url) return;
        testPreviewImg.src = url;
        testPreviewImg.style.display = 'block';
        testResult.innerHTML = 'Анализ...';
        const res = await fetch('/api/liker/test', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({url: url})
        });
        const data = await res.json();
        displayTestResult(data);
    }

    function displayTestResult(data) {
        if (data.error) {
            testResult.innerHTML = `<span style="color: var(--danger);">${data.error}</span>`;
            return;
        }
        const prob = data.probability;
        const percent = data.percentage;
        const verdict = data.verdict;
        const shouldLike = prob > 0.44;
        const verdictColor = verdict === 'АЛЬТУХА' ? '#ff6b6b' : '#4caf50';
        testResult.innerHTML = `
            <div style="font-size: 24px; font-weight: bold; color: ${verdictColor};">${verdict}</div>
            <div style="font-size: 36px; color: var(--accent);">${percent}</div>
            <div>Уверенность: ${data.confidence || 'unknown'}</div>
            <div>${shouldLike ? '✅ Бот поставит лайк' : '❌ Бот не поставит лайк'}</div>
        `;
    }

    function showNotification(message, type = 'info') {
        const notif = document.createElement('div');
        notif.className = 'notification';
        const colors = {success: '#2ed573', error: '#ff4757', warning: '#ffa502', info: '#1e90ff'};
        notif.style.borderLeftColor = colors[type] || colors.info;
        notif.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'}"></i> ${message}`;
        notificationArea.appendChild(notif);
        setTimeout(() => notif.remove(), 5000);
    }

    setInterval(() => {
        if (currentTab && currentTab !== 'liker') {
            loadTab(currentTab);
            loadCounts();
        }
    }, 30000);

    init();
});