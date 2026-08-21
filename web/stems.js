(function () {
    'use strict';

    // ========================
    // 简易 API 请求工具（自动携带登录 token）
    // ========================
    function getToken() {
        return localStorage.getItem('gh_token');
    }

    function apiFetch(url, options) {
        options = options || {};
        options.headers = options.headers || {};
        const token = getToken();
        if (token) {
            options.headers['Authorization'] = 'Bearer ' + token;
        }
        return fetch(url, options);
    }

    // ========================
    // DOM 引用
    // ========================
    const stemFileInput = document.getElementById('stem-file');
    const stemFileNameEl = document.getElementById('stem-file-name');
    const stemSelectAll = document.getElementById('stem-select-all');
    const stemClearAll = document.getElementById('stem-clear-all');
    const stemGrid = document.getElementById('stem-grid');
    const stemSubmit = document.getElementById('stem-submit');
    const stemProgressWrap = document.getElementById('stem-progress-wrap');
    const stemProgressFill = document.getElementById('stem-progress-fill');
    const stemProgressText = document.getElementById('stem-progress-text');
    const stemEta = document.getElementById('stem-eta');
    const stemResult = document.getElementById('stem-result');
    const stemResultText = document.getElementById('stem-result-text');
    const stemDownloadBtn = document.getElementById('stem-download-btn');
    const stemError = document.getElementById('stem-error');

    let stemCurrentFile = null;
    let stemTaskId = null;

    function showFormError(id, msg) {
        document.getElementById(id).textContent = msg || '';
    }

    function getSelectedStems() {
        return Array.from(stemGrid.querySelectorAll('input:checked')).map(i => i.value);
    }

    function updateStemCards() {
        stemGrid.querySelectorAll('.stem-card').forEach(card => {
            const input = card.querySelector('input');
            card.classList.toggle('selected', input.checked);
        });
    }

    stemFileInput.addEventListener('change', () => {
        const file = stemFileInput.files[0];
        stemCurrentFile = file || null;
        stemFileNameEl.textContent = file ? '已选择：' + file.name : '';
    });

    stemGrid.addEventListener('change', updateStemCards);

    stemSelectAll.addEventListener('click', () => {
        stemGrid.querySelectorAll('input').forEach(i => i.checked = true);
        updateStemCards();
    });
    stemClearAll.addEventListener('click', () => {
        stemGrid.querySelectorAll('input').forEach(i => i.checked = false);
        updateStemCards();
    });

    stemSubmit.addEventListener('click', async () => {
        showFormError('stem-error', '');
        const selected = getSelectedStems();
        if (!selected.length) {
            showFormError('stem-error', '请至少选择一个乐器轨道');
            return;
        }
        if (!stemCurrentFile) {
            showFormError('stem-error', '请先上传音频文件');
            return;
        }

        stemSubmit.disabled = true;
        stemProgressWrap.style.display = 'block';
        stemResult.style.display = 'none';
        setStemProgress(0, '正在上传音频...');

        try {
            const formData = new FormData();
            formData.append('file', stemCurrentFile);
            const uploadRes = await fetch('/api/upload', { method: 'POST', body: formData });
            const uploadData = await uploadRes.json();
            if (!uploadData.filename) throw new Error('音频上传失败');

            const separateRes = await apiFetch('/api/separate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ audio_filename: uploadData.filename, selected_stems: selected }),
            });
            const separateData = await separateRes.json();
            if (separateData.error) throw new Error(separateData.error);
            stemTaskId = separateData.task_id;
            pollStemTask(stemTaskId);
        } catch (err) {
            showFormError('stem-error', err.message);
            stemSubmit.disabled = false;
            stemProgressWrap.style.display = 'none';
        }
    });

    function setStemProgress(percent, text) {
        stemProgressFill.style.width = percent + '%';
        stemProgressText.textContent = text || '处理中...';
    }

    function pollStemTask(taskId) {
        const startTime = Date.now();
        const interval = setInterval(async () => {
            try {
                const res = await apiFetch('/api/tasks/' + taskId);
                const data = await res.json();
                if (data.status === 'running') {
                    const elapsed = (Date.now() - startTime) / 1000;
                    const percent = Math.min(95, 10 + elapsed / 6);
                    setStemProgress(percent, data.progress || '正在处理...');
                    stemEta.textContent = '预计剩余时间：' + estimateEta(percent, elapsed);
                } else if (data.status === 'done') {
                    clearInterval(interval);
                    setStemProgress(100, '完成');
                    stemEta.textContent = '';
                    stemSubmit.disabled = false;
                    showStemResult(data);
                } else if (data.status === 'failed') {
                    clearInterval(interval);
                    showFormError('stem-error', '分轨失败：' + (data.error || '未知错误'));
                    stemSubmit.disabled = false;
                    stemProgressWrap.style.display = 'none';
                }
            } catch (e) {
                console.error('stem poll failed', e);
            }
        }, 1500);

        setTimeout(() => {
            clearInterval(interval);
            if (stemSubmit.disabled) {
                showFormError('stem-error', '任务查询超时，请稍后到我的历史中查看。');
                stemSubmit.disabled = false;
                stemProgressWrap.style.display = 'none';
            }
        }, 1800000);
    }

    function estimateEta(percent, elapsed) {
        if (percent <= 5) return '计算中...';
        const total = elapsed / (percent / 100);
        const remaining = Math.max(0, total - elapsed);
        if (remaining < 60) return Math.ceil(remaining) + ' 秒';
        return Math.ceil(remaining / 60) + ' 分钟';
    }

    function showStemResult(data) {
        stemResult.style.display = 'flex';
        const size = data.zip_size ? '(' + formatBytes(data.zip_size) + ')' : '';
        stemResultText.textContent = '已生成 ' + (data.stems || []).join('、') + ' 共 ' + (data.stems || []).length + ' 个轨道 ' + size;
        let url = '/api/download/' + stemTaskId;
        const token = getToken();
        if (token) url += '?token=' + encodeURIComponent(token);
        stemDownloadBtn.href = url;
        stemDownloadBtn.download = data.download_filename || 'stems.zip';
    }

    function formatBytes(bytes) {
        if (!bytes) return '';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
})();
