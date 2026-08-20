(function () {
    'use strict';

    // ========================
    // DOM 引用
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const chatSend = document.getElementById('chat-send');
    const audioBtn = document.getElementById('audio-btn');
    const audioUpload = document.getElementById('audio-upload');
    const surpriseBtn = document.getElementById('surprise-btn');
    const toneBtn = document.getElementById('tone-btn');
    const scoreContainer = document.getElementById('score-container');
    const playBtn = document.getElementById('play-btn');
    const stopBtn = document.getElementById('stop-btn');
    const memoryProfile = document.getElementById('memory-profile');
    const memoryRules = document.getElementById('memory-rules');
    const memoryStats = document.getElementById('memory-stats');
    const historyList = document.getElementById('history-list');

    // ========================
    // 对话逻辑
    // ========================
    let currentAlphaTex = "";

    function appendMessage(role, text) {
        const div = document.createElement('div');
        div.className = 'chat-message ' + role;
        div.textContent = text;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function sendChat(audioFilename) {
        const message = chatInput.value.trim();
        if (!message && !audioFilename) return;

        if (audioFilename) {
            appendMessage('user', '[上传音频] ' + audioFilename);
        } else {
            appendMessage('user', message);
        }
        chatInput.value = '';
        chatSend.disabled = true;

        // 显示进度消息
        const progressId = 'progress-' + Date.now();
        appendMessage('agent', '已提交任务，正在生成谱面...');
        const progressMsg = chatMessages.lastElementChild;
        if (progressMsg) progressMsg.id = progressId;

        try {
            // 1. 提交任务
            const body = { message: message || '' };
            if (audioFilename) body.audio_filename = audioFilename;

            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const data = await res.json();

            if (!data.task_id) {
                throw new Error('服务端未返回 task_id');
            }

            const taskId = data.task_id;

            // 2. 轮询任务状态
            const pollInterval = setInterval(async () => {
                try {
                    const pollRes = await fetch('/api/tasks/' + taskId);
                    const taskData = await pollRes.json();

                    // 更新进度
                    if (taskData.progress) {
                        progressMsg.textContent = taskData.progress;
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }

                    if (taskData.status === 'done') {
                        clearInterval(pollInterval);
                        if (progressMsg) progressMsg.remove();
                        appendMessage('agent', taskData.reply);
                        if (taskData.alphatex) {
                            currentAlphaTex = taskData.alphatex;
                            renderScore(currentAlphaTex);
                        }
                        chatSend.disabled = false;
                        chatInput.focus();
                    } else if (taskData.status === 'failed') {
                        clearInterval(pollInterval);
                        if (progressMsg) progressMsg.remove();
                        appendMessage('agent', '生成失败：' + (taskData.error || '未知错误'));
                        chatSend.disabled = false;
                        chatInput.focus();
                    }
                    // pending / running 继续轮询
                } catch (e) {
                    console.error('poll failed', e);
                }
            }, 1500);

            // 30 分钟超时保护
            setTimeout(() => {
                clearInterval(pollInterval);
                if (progressMsg && progressMsg.parentNode) {
                    progressMsg.remove();
                    appendMessage('agent', '生成超时，请稍后再试。');
                }
                chatSend.disabled = false;
                chatInput.focus();
            }, 1800000);

        } catch (e) {
            if (progressMsg) progressMsg.remove();
            appendMessage('agent', '请求失败：' + e.message);
            chatSend.disabled = false;
            chatInput.focus();
        }
    }

    chatSend.addEventListener('click', () => sendChat());
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendChat();
    });

    // 音频上传
    audioBtn.addEventListener('click', () => audioUpload.click());

    audioUpload.addEventListener('change', async () => {
        const file = audioUpload.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        appendMessage('agent', '正在上传音频...');
        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData,
            });
            const data = await res.json();
            if (data.filename) {
                sendChat(data.filename);
            } else {
                appendMessage('agent', '上传失败');
            }
        } catch (e) {
            appendMessage('agent', '上传失败：' + e.message);
        }
        audioUpload.value = '';
    });

    // 意外选曲
    surpriseBtn.addEventListener('click', async () => {
        appendMessage('agent', '正在翻遍曲库给你挑个意外之喜...');
        try {
            const res = await fetch('/api/surprise-me');
            const data = await res.json();
            if (data.title && data.title !== '无推荐') {
                const msg = '🎲 意外选曲：《' + data.title + '》' + (data.artist ? ' - ' + data.artist : '') + '\n' + (data.reason || '') + '\n\n已帮你生成谱面，看看喜不喜欢！';
                appendMessage('agent', msg);
                chatInput.value = data.title;
                await sendChat();
            } else {
                appendMessage('agent', '曲库还是空的，先让我学几首歌吧。');
            }
        } catch (e) {
            appendMessage('agent', '选曲失败：' + e.message);
        }
    });

    // 推荐音色
    toneBtn.addEventListener('click', async () => {
        const title = (chatInput.value || '').trim();
        if (!title) {
            appendMessage('agent', '请先输入或生成一首曲子，我再帮你推荐音色。');
            return;
        }
        appendMessage('agent', '正在根据《' + title + '》的风格推荐音色...');
        try {
            const res = await fetch('/api/suggest-tone', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: title, artist: '', bpm: 120, style_vector: {}, techniques: [], difficulty: 3 }),
            });
            const data = await res.json();
            const msg = '🎸 推荐音色\n' +
                '吉他：' + data.guitar + '\n' +
                '预设：' + data.preset + '\n' +
                '音箱：' + data.amp + '\n' +
                '效果器：' + (data.effects.join('、') || '无') + '\n' +
                '说明：' + data.description;
            appendMessage('agent', msg);
        } catch (e) {
            appendMessage('agent', '音色推荐失败：' + e.message);
        }
    });

    // ========================
    // alphaTab 渲染
    // ========================
    let alphaTabApi = null;

    function renderScore(alphaTex) {
        // 清空容器，创建新的 API 挂载点
        scoreContainer.innerHTML = '';
        const apiDiv = document.createElement('div');
        apiDiv.id = 'alphaTab-api';
        apiDiv.style.width = '100%';
        scoreContainer.appendChild(apiDiv);

        // 使用 alphaTab 的 alphaTex 渲染模式
        alphaTabApi = new alphaTab.AlphaTabApi(apiDiv, {
            core: {
                tex: true,  // 启用 alphaTex 模式，通过 api.tex() 传内容
            },
            display: {
                layoutMode: alphaTab.LayoutMode.Page,
                staveProfile: alphaTab.StaveProfile.ScoreTab,
                barCountPerPartial: 4,
            },
            player: {
                enablePlayer: true,
                enableCursor: true,
                enableAnimatedBeatCursor: true,
                enableUserInteraction: true,
                soundFont: 'https://cdn.jsdelivr.net/npm/@coderline/alphatab@latest/dist/soundfont/sonivox.sf2',
            },
            notation: {
                elements: {
                    chordDiagrams: false,
                },
            },
        });
        // 传入 alphaTex 内容
        alphaTabApi.tex(alphaTex);

        // 播放按钮控制
        playBtn.onclick = () => {
            if (alphaTabApi) {
                alphaTabApi.playPause();
            }
        };
        stopBtn.onclick = () => {
            if (alphaTabApi) {
                alphaTabApi.stop();
            }
        };
    }

    // ========================
    // 记忆面板
    // ========================
    let previousRulesHash = '';

    function renderMemory(data) {
        // 画像
        memoryProfile.innerHTML = '';
        for (const [key, value] of Object.entries(data.profile)) {
            const row = document.createElement('div');
            row.className = 'memory-row';
            row.innerHTML = '<span class="memory-key">' + key + '</span><span class="memory-value">' + value + '</span>';
            memoryProfile.appendChild(row);
        }

        // 规则（检测新增并高亮）
        memoryRules.innerHTML = '';
        const currentRulesHash = JSON.stringify(data.rules);
        data.rules.forEach((rule, index) => {
            const item = document.createElement('div');
            item.className = 'rule-item';
            if (currentRulesHash !== previousRulesHash && index === data.rules.length - 1) {
                item.classList.add('highlight');
            }
            item.innerHTML = '<span class="rule-text">' + rule.text + '</span><span class="rule-hits">x' + rule.hit_count + '</span>';
            memoryRules.appendChild(item);
        });
        previousRulesHash = currentRulesHash;

        // 统计（episodes_count + cost）
        memoryStats.innerHTML = '';
        const stats = data.cost || {};
        const costLabels = {
            total_tokens_in: '输入 token',
            total_tokens_out: '输出 token',
            total_latency_ms: '总延迟(ms)',
            memory_ops: '记忆操作',
            memory_count: '记忆条数',
        };
        for (const [key, value] of Object.entries(stats)) {
            const row = document.createElement('div');
            row.className = 'memory-row';
            const label = costLabels[key] || key;
            row.innerHTML = '<span class="memory-key">' + label + '</span><span class="memory-value">' + value + '</span>';
            memoryStats.appendChild(row);
        }
        if (typeof data.episodes_count === 'number') {
            const row = document.createElement('div');
            row.className = 'memory-row';
            row.innerHTML = '<span class="memory-key">episodes_count</span><span class="memory-value">' + data.episodes_count + '</span>';
            memoryStats.appendChild(row);
        }
    }

    async function pollMemory() {
        try {
            const res = await fetch('/api/memory');
            const data = await res.json();
            renderMemory(data);
        } catch (e) {
            console.error('memory poll failed', e);
        }
    }

    // 启动轮询
    pollMemory();
    setInterval(pollMemory, 2000);

    // ========================
    // 历史记录
    // ========================
    async function pollHistory() {
        try {
            const res = await fetch('/api/history');
            const data = await res.json();
            historyList.innerHTML = '';
            data.forEach(item => {
                const div = document.createElement('div');
                div.className = 'history-item';
                const date = new Date(item.created_at).toLocaleString('zh-CN', { hour12: false });
                div.innerHTML = '<span class="history-title">' + (item.artist ? item.title + ' - ' + item.artist : item.title) + '</span>' +
                    '<span class="history-meta">' + (item.source || '') + ' ' + date + '</span>';
                div.addEventListener('click', async () => {
                    const detail = await fetch('/api/history/' + item.id).then(r => r.json());
                    if (detail && detail.alphatex) {
                        currentAlphaTex = detail.alphatex;
                        renderScore(currentAlphaTex);
                        appendMessage('agent', '已加载历史谱面：《' + detail.title + '》');
                    }
                });
                historyList.appendChild(div);
            });
        } catch (e) {
            console.error('history poll failed', e);
        }
    }

    pollHistory();
    setInterval(pollHistory, 3000);
    currentAlphaTex = "\\title \"演示曲\"\n\\tempo 120\n\\ts 4 4\n.\n0.3.4 2.3.4 0.2.4 1.2.4 |\n0.3.4 2.3.4 0.2.4 1.2.4 |\n0.3.4 2.3.4 0.2.4 1.2.4 |";
    renderScore(currentAlphaTex);

})();
