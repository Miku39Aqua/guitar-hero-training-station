(function () {
    'use strict';

    // ========================
    // DOM 引用
    // ========================
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
    const downloadGp5Btn = document.getElementById('download-gp5-btn');
    const resizer = document.getElementById('resizer');
    const panelChat = document.querySelector('.panel-chat');
    const panelScore = document.querySelector('.panel-score');
    const panelMemory = document.querySelector('.panel-memory');
    const historyList = document.getElementById('history-list');

    // 记忆面板元素
    const resizerMemory = document.getElementById('resizer-memory');
    const memoryProfileEl = document.getElementById('memory-profile');
    const memoryRulesEl = document.getElementById('memory-rules');
    const memoryRulesCountEl = document.getElementById('memory-rules-count');
    const memoryEpisodesEl = document.getElementById('memory-episodes');
    const memoryCostEl = document.getElementById('memory-cost');

    // 进度条元素
    const progressBar = document.getElementById('progress-bar');
    const progressFill = document.getElementById('progress-fill');
    const progressHandle = document.getElementById('progress-handle');
    const currentTimeEl = document.getElementById('current-time');
    const totalTimeEl = document.getElementById('total-time');

    // 控制面板元素
    const toggleOriginal = document.getElementById('toggle-original');
    const toggleParsed = document.getElementById('toggle-parsed');
    const toggleScore = document.getElementById('toggle-score');
    const volumeOriginal = document.getElementById('volume-original');
    const volumeParsed = document.getElementById('volume-parsed');
    const volumeScore = document.getElementById('volume-score');

    // 顶部用户栏
    const userNameEl = document.getElementById('user-name');
    const authBtn = document.getElementById('auth-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const myHistoryBtn = document.getElementById('my-history-btn');

    // 弹窗
    const authModal = document.getElementById('auth-modal');
    const authModalClose = document.getElementById('auth-modal-close');
    const historyModal = document.getElementById('history-modal');
    const historyModalClose = document.getElementById('history-modal-close');
    const audioModeModal = document.getElementById('audio-mode-modal');
    const audioModeModalClose = document.getElementById('audio-mode-modal-close');
    const audioModeConfirm = document.getElementById('audio-mode-confirm');

    // ========================
    // API 请求工具（自动携带登录 token）
    // ========================
    function apiFetch(url, options) {
        options = options || {};
        options.headers = options.headers || {};
        const token = AuthManager.getToken();
        if (token) {
            options.headers['Authorization'] = 'Bearer ' + token;
        }
        return fetch(url, options);
    }

    // ========================
    // 用户认证管理
    // ========================
    const AuthManager = {
        user: null,

        getToken() {
            return localStorage.getItem('gh_token');
        },
        setToken(token) {
            localStorage.setItem('gh_token', token);
        },
        clearToken() {
            localStorage.removeItem('gh_token');
            this.user = null;
        },

        async fetchMe() {
            const token = this.getToken();
            if (!token) {
                this.user = null;
                this.updateUI();
                return;
            }
            try {
                const res = await apiFetch('/api/auth/me');
                if (res.ok) {
                    this.user = await res.json();
                } else {
                    this.clearToken();
                }
            } catch (e) {
                this.user = null;
            }
            this.updateUI();
        },

        updateUI() {
            if (this.user) {
                userNameEl.textContent = this.user.username;
                authBtn.style.display = 'none';
                logoutBtn.style.display = 'inline-block';
            } else {
                userNameEl.textContent = '';
                authBtn.style.display = 'inline-block';
                logoutBtn.style.display = 'none';
            }
        },

        isLoggedIn() {
            return !!this.user;
        },

        async login(username, password, remember) {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, remember_me: remember }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || '登录失败');
            this.setToken(data.access_token);
            await this.fetchMe();
            return data;
        },

        async register(username, email, password) {
            const res = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || '注册失败');
            this.setToken(data.access_token);
            await this.fetchMe();
            return data;
        },

        async forgotPassword(email) {
            const res = await fetch('/api/auth/forgot-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
            return res.json();
        },

        async resetPassword(token, newPassword) {
            const res = await fetch('/api/auth/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, new_password: newPassword }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || '重置失败');
            return data;
        },

        logout() {
            this.clearToken();
            this.updateUI();
            fetch('/api/auth/logout', { method: 'POST' }).catch(() => {});
        }
    };

    // ========================
    // 弹窗通用逻辑
    // ========================
    function openModal(modal) {
        modal.style.display = 'flex';
    }
    function closeModal(modal) {
        modal.style.display = 'none';
    }
    function closeAllModals() {
        [authModal, historyModal, audioModeModal].forEach(closeModal);
    }

    authBtn.addEventListener('click', () => openModal(authModal));
    authModalClose.addEventListener('click', () => closeModal(authModal));
    historyModalClose.addEventListener('click', () => closeModal(historyModal));
    audioModeModalClose.addEventListener('click', () => closeModal(audioModeModal));
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) closeModal(e.target);
    });
    logoutBtn.addEventListener('click', () => AuthManager.logout());

    // ========================
    // 登录/注册/忘记密码 UI
    // ========================
    const authTabs = document.querySelectorAll('.auth-tab');
    const authForms = document.querySelectorAll('.auth-form');

    function switchAuthTab(tabName) {
        authTabs.forEach(t => t.classList.toggle('active', t.dataset.tab === tabName));
        authForms.forEach(f => f.classList.toggle('active', f.id === tabName + '-form'));
    }

    authTabs.forEach(tab => {
        tab.addEventListener('click', () => switchAuthTab(tab.dataset.tab));
    });

    function showFormError(id, msg) {
        document.getElementById(id).textContent = msg || '';
    }
    function showFormSuccess(id, msg) {
        document.getElementById(id).textContent = msg || '';
    }

    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        showFormError('login-error', '');
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value;
        const remember = document.getElementById('login-remember').checked;
        try {
            await AuthManager.login(username, password, remember);
            closeModal(authModal);
            appendMessage('agent', '登录成功，欢迎回来！');
        } catch (err) {
            showFormError('login-error', err.message);
        }
    });

    document.getElementById('register-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        showFormError('register-error', '');
        const username = document.getElementById('register-username').value.trim();
        const email = document.getElementById('register-email').value.trim();
        const password = document.getElementById('register-password').value;
        try {
            await AuthManager.register(username, email, password);
            closeModal(authModal);
            appendMessage('agent', '注册成功，已自动登录！');
        } catch (err) {
            showFormError('register-error', err.message);
        }
    });

    document.getElementById('forgot-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        showFormError('forgot-error', '');
        showFormSuccess('forgot-success', '');
        const email = document.getElementById('forgot-email').value.trim();
        try {
            const data = await AuthManager.forgotPassword(email);
            showFormSuccess('forgot-success', data.reset_url
                ? '开发环境：' + data.reset_url
                : '如果该邮箱已注册，重置链接将发送至邮箱。');
        } catch (err) {
            showFormError('forgot-error', err.message);
        }
    });

    document.getElementById('reset-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        showFormError('reset-error', '');
        showFormSuccess('reset-success', '');
        const token = document.getElementById('reset-token') ? document.getElementById('reset-token').value : '';
        const password = document.getElementById('reset-password').value;
        try {
            await AuthManager.resetPassword(token, password);
            showFormSuccess('reset-success', '密码已重置，请使用新密码登录。');
            setTimeout(() => switchAuthTab('login'), 1500);
        } catch (err) {
            showFormError('reset-error', err.message);
        }
    });

    // 从 URL 参数进入重置密码页
    const urlParams = new URLSearchParams(window.location.search);
    const resetTokenFromUrl = urlParams.get('reset_token');
    if (resetTokenFromUrl) {
        const resetForm = document.getElementById('reset-form');
        let hidden = document.getElementById('reset-token');
        if (!hidden) {
            hidden = document.createElement('input');
            hidden.type = 'hidden';
            hidden.id = 'reset-token';
            resetForm.insertBefore(hidden, resetForm.firstChild);
        }
        hidden.value = resetTokenFromUrl;
        switchAuthTab('reset');
        openModal(authModal);
    }

    // ========================
    // 我的历史
    // ========================
    const myHistoryList = document.getElementById('my-history-list');
    const historyLoginTip = document.getElementById('history-login-tip');
    const historyPagination = document.getElementById('history-pagination');
    const historyPrev = document.getElementById('history-prev');
    const historyNext = document.getElementById('history-next');
    const historyPageInfo = document.getElementById('history-page-info');

    let historyState = { page: 1, pageSize: 10, total: 0 };

    myHistoryBtn.addEventListener('click', () => {
        openModal(historyModal);
        loadMyHistory(1);
    });

    historyPrev.addEventListener('click', () => loadMyHistory(historyState.page - 1));
    historyNext.addEventListener('click', () => loadMyHistory(historyState.page + 1));

    async function loadMyHistory(page) {
        myHistoryList.innerHTML = '';
        historyLoginTip.style.display = 'none';
        historyPagination.style.display = 'none';

        if (!AuthManager.isLoggedIn()) {
            historyLoginTip.style.display = 'block';
            myHistoryList.innerHTML = '<div class="form-hint">请先登录以查看个人历史记录。</div>';
            return;
        }

        try {
            const res = await apiFetch('/api/my-history?page=' + page + '&page_size=' + historyState.pageSize);
            const data = await res.json();
            historyState.page = data.page;
            historyState.total = data.total;

            if (!data.items || !data.items.length) {
                myHistoryList.innerHTML = '<div class="form-hint">暂无历史记录。</div>';
                return;
            }

            data.items.forEach(item => {
                const div = document.createElement('div');
                div.className = 'history-item';
                const created = new Date(item.created_at).toLocaleString('zh-CN', { hour12: false });
                const types = JSON.parse(item.extraction_type || '[]').join('、') || '音频';
                div.innerHTML = '<div class="history-title">' + escapeHtml(item.filename) + '</div>' +
                    '<div class="history-meta">' + types + ' · ' + item.status + ' · ' + created + '</div>';
                if (item.zip_path) {
                    const dl = document.createElement('a');
                    dl.className = 'btn-download btn-sm';
                    dl.textContent = '下载';
                    let url = '/api/download/' + item.task_id;
                    const token = AuthManager.getToken();
                    if (token) url += '?token=' + encodeURIComponent(token);
                    dl.href = url;
                    dl.download = item.filename + '_stems.zip';
                    div.appendChild(dl);
                }
                myHistoryList.appendChild(div);
            });

            const totalPages = Math.ceil(data.total / data.page_size) || 1;
            historyPageInfo.textContent = data.page + ' / ' + totalPages;
            historyPrev.disabled = data.page <= 1;
            historyNext.disabled = data.page >= totalPages;
            historyPagination.style.display = 'flex';
        } catch (e) {
            myHistoryList.innerHTML = '<div class="form-error">加载失败：' + e.message + '</div>';
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ========================
    // 可拖拽分隔条
    // ========================
    if (resizer && panelChat && panelScore) {
        let isResizing = false;
        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            resizer.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            e.preventDefault();
        });
        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            const newChatWidth = e.clientX;
            if (newChatWidth >= 280 && newChatWidth <= (window.innerWidth - 320)) {
                panelChat.style.width = newChatWidth + 'px';
            }
        });
        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                resizer.classList.remove('active');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });
    }

    if (resizerMemory && panelMemory) {
        let isResizingMemory = false;
        resizerMemory.addEventListener('mousedown', (e) => {
            isResizingMemory = true;
            resizerMemory.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            e.preventDefault();
        });
        document.addEventListener('mousemove', (e) => {
            if (!isResizingMemory) return;
            const newMemoryWidth = window.innerWidth - e.clientX;
            if (newMemoryWidth >= 240 && newMemoryWidth <= (window.innerWidth - 320)) {
                panelMemory.style.width = newMemoryWidth + 'px';
            }
        });
        document.addEventListener('mouseup', () => {
            if (isResizingMemory) {
                isResizingMemory = false;
                resizerMemory.classList.remove('active');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });
    }

    // ========================
    // 全局状态
    // ========================
    let currentAlphaTex = "";
    let currentTaskId = "";
    let currentSongMeta = { title: '', artist: '', bpm: 120, style_vector: {}, techniques: [], difficulty: 3 };
    let currentAudioMode = "song";
    let currentAudioFilename = null;
    let alphaTabApi = null;
    let isScorePlaying = false;

    const audioTracks = {
        original: { audio: null, volume: 0.8, muted: false, enabled: false },
        parsed: { audio: null, volume: 0.8, muted: false, enabled: false },
        score: { volume: 0.8, muted: false, enabled: true },
    };

    // ========================
    // 音频轨道初始化
    // ========================
    let audioTracksInitialized = false;
    function initAudioTracks() {
        if (audioTracksInitialized) return;
        audioTracksInitialized = true;

        const originalAudio = new Audio();
        originalAudio.crossOrigin = "anonymous";
        audioTracks.original.audio = originalAudio;

        const parsedAudio = new Audio();
        parsedAudio.crossOrigin = "anonymous";
        audioTracks.parsed.audio = parsedAudio;

        originalAudio.addEventListener('play', () => {
            if (audioTracks.score.enabled && alphaTabApi && alphaTabApi.player) {
                alphaTabApi.player.play();
            }
            if (audioTracks.parsed.enabled && audioTracks.parsed.audio) {
                audioTracks.parsed.audio.currentTime = originalAudio.currentTime;
                audioTracks.parsed.audio.play().catch(() => {});
            }
        });

        originalAudio.addEventListener('pause', () => {
            if (alphaTabApi && alphaTabApi.player) {
                alphaTabApi.player.pause();
            }
            if (audioTracks.parsed.audio) {
                audioTracks.parsed.audio.pause();
            }
        });

        originalAudio.addEventListener('seeked', () => {
            if (alphaTabApi && alphaTabApi.player) {
                alphaTabApi.player.timePosition = originalAudio.currentTime * 1000;
            }
            if (audioTracks.parsed.audio) {
                audioTracks.parsed.audio.currentTime = originalAudio.currentTime;
            }
        });
    }

    function bindAlphaTabEvents() {
        if (!alphaTabApi) return;

        // 播放位置变化：官方事件是 api.playerPositionChanged，args.currentTime/endTime 单位是毫秒
        alphaTabApi.playerPositionChanged.on((args) => {
            const time = args.currentTime / 1000;
            if (audioTracks.original.enabled && audioTracks.original.audio && !audioTracks.original.audio.paused) {
                if (Math.abs(audioTracks.original.audio.currentTime - time) > 0.5) {
                    audioTracks.original.audio.currentTime = time;
                }
            }
            if (audioTracks.parsed.enabled && audioTracks.parsed.audio && !audioTracks.parsed.audio.paused) {
                if (Math.abs(audioTracks.parsed.audio.currentTime - time) > 0.5) {
                    audioTracks.parsed.audio.currentTime = time;
                }
            }
            updateProgressUI();
        });

        // 播放状态变化：官方事件是 api.playerStateChanged，state === PlayerState.Playing (1)
        alphaTabApi.playerStateChanged.on((args) => {
            isScorePlaying = args.state === alphaTab.synth.PlayerState.Playing;
            playBtn.textContent = isScorePlaying ? '暂停' : '播放';
            if (!isScorePlaying) {
                updateProgressUI();
            }
        });
    }

    function updateProgressUI(force) {
        if (!alphaTabApi || !alphaTabApi.player) return;
        if (isDraggingProgress && !force) return;
        const currentTime = alphaTabApi.player.timePosition || 0;
        const totalTime = alphaTabApi.endTime || 1;
        const progress = (currentTime / totalTime) * 100;
        progressFill.style.width = progress + '%';
        progressHandle.style.left = progress + '%';
        currentTimeEl.textContent = formatTime(currentTime / 1000);
        totalTimeEl.textContent = formatTime(totalTime / 1000);
    }

    function formatTime(seconds) {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return m + ':' + (s < 10 ? '0' : '') + s;
    }

    // ========================
    // 进度条拖拽
    // ========================
    let isDraggingProgress = false;

    progressBar.addEventListener('mousedown', (e) => {
        isDraggingProgress = true;
        updateProgressFromMouse(e);
    });

    document.addEventListener('mousemove', (e) => {
        if (isDraggingProgress) {
            updateProgressFromMouse(e);
        }
    });

    document.addEventListener('mouseup', () => {
        if (isDraggingProgress) {
            isDraggingProgress = false;
        }
    });

    function updateProgressFromMouse(e) {
        if (!alphaTabApi || !alphaTabApi.player) return;
        const rect = progressBar.getBoundingClientRect();
        let x = e.clientX - rect.left;
        x = Math.max(0, Math.min(x, rect.width));
        const progress = x / rect.width;
        const totalTime = alphaTabApi.endTime || 0;
        const newTime = progress * totalTime;
        alphaTabApi.player.timePosition = newTime;

        updateProgressUI(true);

        const newTimeSeconds = newTime / 1000;
        if (audioTracks.original.audio && audioTracks.original.enabled) {
            audioTracks.original.audio.currentTime = newTimeSeconds;
        }
        if (audioTracks.parsed.audio && audioTracks.parsed.enabled) {
            audioTracks.parsed.audio.currentTime = newTimeSeconds;
        }
    }

    // ========================
    // 播放控制
    // ========================
    function playAll() {
        if (!alphaTabApi) return;

        if (audioTracks.score.enabled) {
            alphaTabApi.player.play();
        }

        if (audioTracks.original.enabled && audioTracks.original.audio && audioTracks.original.audio.src) {
            audioTracks.original.audio.play().catch(() => {});
        }

        if (audioTracks.parsed.enabled && audioTracks.parsed.audio && audioTracks.parsed.audio.src) {
            audioTracks.parsed.audio.play().catch(() => {});
        }
    }

    function pauseAll() {
        if (alphaTabApi && alphaTabApi.player) {
            alphaTabApi.player.pause();
        }
        if (audioTracks.original.audio) {
            audioTracks.original.audio.pause();
        }
        if (audioTracks.parsed.audio) {
            audioTracks.parsed.audio.pause();
        }
    }

    function stopAll() {
        if (alphaTabApi && alphaTabApi.player) {
            alphaTabApi.player.stop();
        }
        if (audioTracks.original.audio) {
            audioTracks.original.audio.pause();
            audioTracks.original.audio.currentTime = 0;
        }
        if (audioTracks.parsed.audio) {
            audioTracks.parsed.audio.pause();
            audioTracks.parsed.audio.currentTime = 0;
        }
        updateProgressUI();
    }

    playBtn.addEventListener('click', () => {
        if (!alphaTabApi || !alphaTabApi.player) return;
        if (isScorePlaying) {
            pauseAll();
        } else {
            playAll();
        }
        // playBtn 文案由 playerStateChanged 事件统一更新，这里不再重复设置
    });

    stopBtn.addEventListener('click', () => {
        stopAll();
        playBtn.textContent = '播放';
    });

    // ========================
    // 音轨开关
    // ========================
    toggleOriginal.addEventListener('click', () => {
        audioTracks.original.enabled = !audioTracks.original.enabled;
        if (audioTracks.original.enabled) {
            toggleOriginal.classList.add('active');
            toggleOriginal.textContent = '开';
            if (audioTracks.original.audio && audioTracks.original.audio.src) {
                audioTracks.original.audio.play().catch(() => {});
            }
        } else {
            toggleOriginal.classList.remove('active');
            toggleOriginal.textContent = '静音';
            if (audioTracks.original.audio) {
                audioTracks.original.audio.pause();
            }
        }
    });

    toggleParsed.addEventListener('click', () => {
        audioTracks.parsed.enabled = !audioTracks.parsed.enabled;
        if (audioTracks.parsed.enabled) {
            toggleParsed.classList.add('active');
            toggleParsed.textContent = '开';
            if (audioTracks.parsed.audio && audioTracks.parsed.audio.src) {
                audioTracks.parsed.audio.play().catch(() => {});
            }
        } else {
            toggleParsed.classList.remove('active');
            toggleParsed.textContent = '静音';
            if (audioTracks.parsed.audio) {
                audioTracks.parsed.audio.pause();
            }
        }
    });

    toggleScore.addEventListener('click', () => {
        audioTracks.score.enabled = !audioTracks.score.enabled;
        if (audioTracks.score.enabled) {
            toggleScore.classList.add('active');
            toggleScore.textContent = '开';
            if (alphaTabApi && alphaTabApi.player) {
                alphaTabApi.player.masterVolume = parseInt(volumeScore.value) / 100;
            }
        } else {
            toggleScore.classList.remove('active');
            toggleScore.textContent = '静音';
            if (alphaTabApi && alphaTabApi.player) {
                alphaTabApi.player.masterVolume = 0;
            }
        }
    });

    // ========================
    // 音量控制
    // ========================
    volumeOriginal.addEventListener('input', () => {
        const vol = parseInt(volumeOriginal.value) / 100;
        audioTracks.original.volume = vol;
        if (audioTracks.original.audio) {
            audioTracks.original.audio.volume = vol;
        }
    });

    volumeParsed.addEventListener('input', () => {
        const vol = parseInt(volumeParsed.value) / 100;
        audioTracks.parsed.volume = vol;
        if (audioTracks.parsed.audio) {
            audioTracks.parsed.audio.volume = vol;
        }
    });

    volumeScore.addEventListener('input', () => {
        const vol = parseInt(volumeScore.value) / 100;
        audioTracks.score.volume = vol;
        if (alphaTabApi && alphaTabApi.player) {
            alphaTabApi.player.masterVolume = vol;
        }
    });

    // ========================
    // alphaTab 渲染
    // ========================
    function renderScore(alphaTex, audioFilename) {
        if (audioFilename) {
            currentAudioFilename = audioFilename;
            if (audioTracks.original.audio) {
                audioTracks.original.audio.src = '/api/audio/' + encodeURIComponent(audioFilename);
                audioTracks.original.enabled = true;
                toggleOriginal.classList.add('active');
                toggleOriginal.textContent = '开';
                audioTracks.original.audio.volume = parseInt(volumeOriginal.value) / 100;
            }
        }

        scoreContainer.innerHTML = '';
        const apiDiv = document.createElement('div');
        apiDiv.id = 'alphaTab-api';
        apiDiv.style.width = '100%';
        scoreContainer.appendChild(apiDiv);

        alphaTabApi = new alphaTab.AlphaTabApi(apiDiv, {
            core: { tex: true },
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
                scrollElement: scoreContainer,
                soundFont: 'https://cdn.jsdelivr.net/npm/@coderline/alphatab@latest/dist/soundfont/sonivox.sf2',
            },
            notation: {
                elements: { chordDiagrams: false },
            },
        });

        if (alphaTabApi.renderStarted && typeof alphaTabApi.renderStarted.on === 'function') {
            alphaTabApi.renderStarted.on(() => {
                console.log('[alphaTab] render started');
            });
        }

        if (alphaTabApi.renderFinished && typeof alphaTabApi.renderFinished.on === 'function') {
            alphaTabApi.renderFinished.on(() => {
                console.log('[alphaTab] render finished, masterBars:', alphaTabApi.score?.masterBars?.length);
                if (alphaTabApi.player) {
                    updateProgressUI();
                }
            });
        }

        if (alphaTabApi.error && typeof alphaTabApi.error.on === 'function') {
            alphaTabApi.error.on((err) => {
                console.error('[alphaTab] error:', err);
                appendMessage('agent', '谱面渲染出错：' + (err.message || '未知错误'));
            });
        }

        try {
            alphaTabApi.tex(alphaTex);
        } catch (err) {
            console.error('[alphaTab] tex error:', err);
            appendMessage('agent', '谱面数据解析失败：' + err.message);
            return;
        }

        initAudioTracks();

        setTimeout(() => {
            bindAlphaTabEvents();
            if (alphaTabApi.player) {
                updateProgressUI();
            }
        }, 100);

        if (alphaTabApi.player) {
            alphaTabApi.player.masterVolume = parseInt(volumeScore.value) / 100;
        }

        updateProgressUI();

        if (!alphaTex || alphaTex.trim().length < 10 || !alphaTex.includes('|')) {
            console.warn('[renderScore] alphaTex seems empty, no measures will render');
        }
    }

    // ========================
    // 对话逻辑
    // ========================
    async function fetchSongMeta(title) {
        const candidates = [title, encodeURIComponent(title)];
        for (const name of candidates) {
            try {
                const res = await fetch('features/' + name + '.json');
                if (!res.ok) continue;
                const data = await res.json();
                return {
                    title: data.title || title,
                    artist: data.artist || '',
                    bpm: data.bpm || 120,
                    style_vector: data.style_vector || {},
                    techniques: data.techniques || [],
                    difficulty: data.difficulty || 3,
                };
            } catch (e) {
                // ignore
            }
        }
        return null;
    }

    function appendMessage(role, text, feedbackContext) {
        const div = document.createElement('div');
        div.className = 'chat-message ' + role;
        div.textContent = text;
        chatMessages.appendChild(div);

        if (role === 'agent' && feedbackContext) {
            const fb = document.createElement('div');
            fb.className = 'feedback-btns';
            fb.innerHTML = '<button class="btn-feedback" data-value="👍">👍</button>' +
                           '<button class="btn-feedback" data-value="👎">👎</button>';
            fb.querySelectorAll('.btn-feedback').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const value = btn.getAttribute('data-value');
                    await sendFeedback(feedbackContext, value);
                    fb.style.display = 'none';
                });
            });
            chatMessages.appendChild(fb);
        }

        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function sendFeedback(context, value) {
        try {
            await apiFetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_input: context.user_input || '',
                    agent_output: context.agent_output || '',
                    feedback: value,
                }),
            });
        } catch (e) {
            console.error('feedback failed', e);
        }
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

        const progressId = 'progress-' + Date.now();
        appendMessage('agent', '已提交任务，正在生成谱面...');
        const progressMsg = chatMessages.lastElementChild;
        if (progressMsg) progressMsg.id = progressId;

        try {
            const body = { message: message || '' };
            if (audioFilename) body.audio_filename = audioFilename;
            body.audio_mode = currentAudioMode;

            const res = await apiFetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const data = await res.json();

            if (!data.task_id) {
                throw new Error('服务端未返回 task_id');
            }

            const taskId = data.task_id;
            currentTaskId = taskId;

            const pollInterval = setInterval(async () => {
                try {
                    const pollRes = await fetch('/api/tasks/' + taskId);
                    const taskData = await pollRes.json();

                    if (taskData.progress) {
                        progressMsg.textContent = taskData.progress;
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }

                    if (taskData.status === 'done') {
                        clearInterval(pollInterval);
                        if (progressMsg) progressMsg.remove();
                        appendMessage('agent', taskData.reply, {
                            user_input: message || (audioFilename || ''),
                            agent_output: taskData.reply,
                        });
                        if (taskData.alphatex) {
                            currentAlphaTex = taskData.alphatex;
                            renderScore(currentAlphaTex, audioFilename);

                            if (taskData.parsed_audio_filename && audioTracks.parsed.audio) {
                                const parsedSrc = '/api/audio/' + encodeURIComponent(taskData.parsed_audio_filename);
                                audioTracks.parsed.audio.src = parsedSrc;
                                audioTracks.parsed.audio.load();
                                audioTracks.parsed.enabled = true;
                                toggleParsed.classList.add('active');
                                toggleParsed.textContent = '开';
                                audioTracks.parsed.audio.volume = parseInt(volumeParsed.value) / 100;
                                console.log('[parsed track] set src:', parsedSrc);
                            }

                            const infoMsg = '谱面已生成：' + (taskData.title || '未命名');
                            appendMessage('agent', infoMsg);
                        } else {
                            appendMessage('agent', '生成完成，但未返回谱面数据。');
                        }
                        if (downloadGp5Btn) downloadGp5Btn.disabled = false;
                        const guessedTitle = (message || chatInput.value || '').trim();
                        if (guessedTitle) {
                            fetchSongMeta(guessedTitle).then(meta => {
                                if (meta) currentSongMeta = meta;
                            });
                        }
                        chatSend.disabled = false;
                        chatInput.focus();
                    } else if (taskData.status === 'failed') {
                        clearInterval(pollInterval);
                        if (progressMsg) progressMsg.remove();
                        appendMessage('agent', '生成失败：' + (taskData.error || '未知错误'), {
                            user_input: message || (audioFilename || ''),
                            agent_output: '生成失败：' + (taskData.error || '未知错误'),
                        });
                        chatSend.disabled = false;
                        chatInput.focus();
                    }
                } catch (e) {
                    console.error('poll failed', e);
                }
            }, 1500);

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

    // ========================
    // 音频上传（带模式选择）
    // ========================
    audioBtn.addEventListener('click', () => {
        openModal(audioModeModal);
    });

    audioModeConfirm.addEventListener('click', () => {
        const checked = audioModeModal.querySelector('input[name="audio-mode"]:checked');
        currentAudioMode = checked ? checked.value : 'song';
        closeModal(audioModeModal);
        audioUpload.click();
    });

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

    // ========================
    // 意外选曲
    // ========================
    surpriseBtn.addEventListener('click', async () => {
        appendMessage('agent', '正在翻遍曲库给你挑个意外之喜...');
        try {
            const res = await fetch('/api/surprise-me');
            const data = await res.json();
            if (data.title && data.title !== '无推荐') {
                const msg = '意外选曲：《' + data.title + '》' + (data.artist ? ' - ' + data.artist : '') + '\n' + (data.reason || '') + '\n\n已帮你生成谱面，看看喜不喜欢！';
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

    // ========================
    // 推荐音色
    // ========================
    toneBtn.addEventListener('click', async () => {
        const title = (chatInput.value || currentSongMeta.title || '').trim();
        if (!title) {
            appendMessage('agent', '请先输入或生成一首曲子，我再帮你推荐音色。');
            return;
        }
        appendMessage('agent', '正在根据《' + title + '》的风格推荐音色...');
        try {
            const meta = await fetchSongMeta(title);
            const body = meta || {
                title: title,
                artist: '',
                bpm: 120,
                style_vector: {},
                techniques: [],
                difficulty: 3,
            };
            const res = await apiFetch('/api/suggest-tone', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const data = await res.json();
            const msg = '推荐音色\n' +
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
    // 历史记录（全局最近生成）
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
    setInterval(pollHistory, 5000);

    // ========================
    // 记忆面板
    // ========================
    let lastMemorySnapshot = null;

    function flashHighlight(el) {
        if (!el) return;
        el.classList.remove('memory-flash');
        // 触发重排以重启动画
        void el.offsetWidth;
        el.classList.add('memory-flash');
    }

    function renderProfile(profile) {
        const entries = Object.entries(profile || {});
        if (entries.length === 0) {
            memoryProfileEl.innerHTML = '暂无画像数据';
            return;
        }
        memoryProfileEl.innerHTML = entries.map(([key, value]) => {
            const text = typeof value === 'object' ? JSON.stringify(value) : String(value);
            return '<div class="memory-kv"><span class="memory-key">' + escapeHtml(key) + '</span><span class="memory-value">' + escapeHtml(text) + '</span></div>';
        }).join('');
    }

    function renderRules(rules) {
        if (!rules || rules.length === 0) {
            memoryRulesEl.innerHTML = '暂无规则';
            return;
        }
        memoryRulesEl.innerHTML = rules.map(rule =>
            '<div class="memory-rule-item">' + escapeHtml(rule.text || '') +
            '<span class="memory-hit">×' + (rule.hit_count || 1) + '</span></div>'
        ).join('');
    }

    function renderCost(cost) {
        cost = cost || {};
        memoryCostEl.innerHTML =
            '<div class="memory-kv"><span class="memory-key">输入 tokens</span><span class="memory-value">' + (cost.total_tokens_in || 0) + '</span></div>' +
            '<div class="memory-kv"><span class="memory-key">输出 tokens</span><span class="memory-value">' + (cost.total_tokens_out || 0) + '</span></div>' +
            '<div class="memory-kv"><span class="memory-key">累计耗时</span><span class="memory-value">' + Math.round(cost.total_latency_ms || 0) + 'ms</span></div>' +
            '<div class="memory-kv"><span class="memory-key">记忆操作次数</span><span class="memory-value">' + (cost.memory_ops || 0) + '</span></div>';
    }

    async function pollMemory() {
        try {
            const res = await fetch('/api/memory');
            if (!res.ok) return;
            const data = await res.json();

            renderProfile(data.profile);
            renderRules(data.rules);
            memoryRulesCountEl.textContent = data.rules ? String(data.rules.length) : '0';
            memoryEpisodesEl.textContent = '情景数：' + (data.episodes_count || 0);
            renderCost(data.cost);

            if (lastMemorySnapshot) {
                if (JSON.stringify(data.profile) !== JSON.stringify(lastMemorySnapshot.profile)) {
                    flashHighlight(document.getElementById('memory-profile-section'));
                }
                if ((data.rules || []).length !== (lastMemorySnapshot.rules || []).length ||
                    JSON.stringify(data.rules) !== JSON.stringify(lastMemorySnapshot.rules)) {
                    flashHighlight(document.getElementById('memory-rules-section'));
                }
                if (data.episodes_count !== lastMemorySnapshot.episodes_count) {
                    flashHighlight(document.getElementById('memory-episodes-section'));
                }
                if (JSON.stringify(data.cost) !== JSON.stringify(lastMemorySnapshot.cost)) {
                    flashHighlight(document.getElementById('memory-cost-section'));
                }
            }
            lastMemorySnapshot = data;
        } catch (e) {
            console.error('memory poll failed', e);
        }
    }

    pollMemory();
    setInterval(pollMemory, 2000);

    // 初始演示曲
    currentAlphaTex = "\\title \"演示曲\"\n\\tempo 120\n\\ts 4 4\n.\n0.3.4 2.3.4 0.2.4 1.2.4 |\n0.3.4 2.3.4 0.2.4 1.2.4 |\n0.3.4 2.3.4 0.2.4 1.2.4 |";
    renderScore(currentAlphaTex);

    // GP5 下载
    if (downloadGp5Btn) {
        downloadGp5Btn.addEventListener('click', async () => {
            if (!currentTaskId) {
                appendMessage('agent', '请先生成谱面，再下载 GP5。');
                return;
            }
            try {
                const res = await fetch('/api/export-gp5/' + currentTaskId);
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.error || '下载失败');
                }
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = (res.headers.get('content-disposition') || '').split('filename=')[1]?.replace(/"/g, '') || 'tab.gp5';
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
            } catch (e) {
                appendMessage('agent', 'GP5 下载失败：' + e.message);
            }
        });
    }

    // ========================
    // 初始化登录状态
    // ========================
    AuthManager.fetchMe();
})();
