/* ─────────────────────────────────────────────
   MindBuddi — App Logic (Clean Version: 3 Tracks + 4 Dynamic Suggestions)
   ───────────────────────────────────────────── */

const API_BASE = window.location.origin;
const VIEW_MODE_KEY = 'mindbuddi-view-mode';
const MOBILE_VIEWPORT_CONTENT = 'width=device-width, initial-scale=1.0';
const DESKTOP_VIEWPORT_WIDTH = 1200;
let history = [];
let currentTrack = 'counseling';
let isLoading = false;
let currentLang = localStorage.getItem('lang') || 'ko';
let currentProfile = {
    mbti: localStorage.getItem('profile_mbti') || null,
    zodiac: localStorage.getItem('profile_zodiac') || null
};
let currentVoice = localStorage.getItem('mindbuddi_voice') || 'buddi';
let activeUtterance = null;
let activeAudio = null;
let activeVoiceProgressTimer = null;


// ── i18n Dictionary ──────────────────────────────────────────
const i18n = {
    ko: {
        subtitle: "붓다지혜마음케어",
        newChat: "새 상담 시작",
        counselMode: "상담 모드 선택",
        counseling: "고민 상담",
        sutraQna: "경전 질문",
        saju: "사주 명리",
        infoTitle: "🪷 상담 안내",
        infoText: "중아함경 등 팔만대장경의 지혜를 바탕으로 마음의 안정과 위로를 드립니다.",
        voiceBtn: "🎙️ 음성 기능 준비 중",
        sutrasBadge: "📖 팔만대장경 지혜 상담",
        statusReady: "상담 준비 완료",
        inputPlaceholder: "마음속의 이야기를 적어주세요…",
        inputHint: "Enter로 전송 · Shift+Enter로 줄바꿈 · 팔만대장경 기반 마음 상담",
        setupTitle: "MindBuddhi에 오신 것을 환영합니다",
        setupLangTitle: "🌐 언어 선택 (Language)",
        setupLangDesc: "선호하시는 언어를 선택해주세요.",
        setupDesc: "<strong>Buddhi(부디)</strong>는 산스크리트어로 지성, 지능, 그리고 고차원적인 지혜를 뜻합니다. 단순한 지식을 넘어 사물의 본질을 꿰뚫어보는 직관적인 통찰력이자 참된 깨어남을 의미합니다.",
        setupVoiceTitle: "🎙️ 상담 목소리 선택",
        setupVoiceDesc: "당신의 마음을 다독여 줄 목소리를 선택해주세요.",
        setupVoiceOption1: "부디 (Buddhi)",
        setupVoiceTag1: "\uc2e4\ud5d8\uc6a9",
        setupVoiceOption2: "AI 목소리",
        setupVoiceTag2: "준비 중입니다",
        setupStartBtn: "지혜의 여정 시작하기",
        consentText: "더 나은 상담 서비스를 위한 상담 데이터 수집 및 이용에 동의합니다.",
        mbti_infj: "옹호자 (INFJ)",
        loadingStatus1: "마음의 소리를 듣고 있습니다...",
        loadingStatus2: "팔만대장경에서 지혜를 찾는 중입니다...",
        loadingStatus3: "나눌 말씀을 다듬고 있습니다...",
        tracks: {
            counseling: {
                intro: "안녕하세요. 저는 팔만대장경의 가르침을 바탕으로 마음을 돌봐드리는 **MindBuddhi**입니다.\n\n오늘 마음속에 무엇이 자리하고 있나요? 불안, 외로움, 슬픔, 혹은 그 어떤 것이든 편안하게 나눠주세요. 성현의 지혜로 함께 바라보겠습니다. 🙏",
                questions: ["반복되는 불안함에서 벗어나는 부처님의 가르침이 궁금해요.", "대인관계에서 오는 스트레스와 상처를 어떻게 치유할까요?", "불확실한 미래에 대한 두려움을 다스리는 지혜를 들려주세요.", "과거의 후회와 집착을 내려놓고 현재를 깊게 사는 법은 무엇인가요?"]
            },
            inquiry: {
                intro: "팔만대장경의 방대한 지혜 속에서 답을 찾아드리는 **경전 질문 모드**입니다. 궁금하신 부처님의 가르침이나 개념이 있으신가요? 📖",
                questions: ["중아함경 속 고통의 근본 원인과 해결 방안에 대해 알려주세요.", "팔정도가 현대인의 바쁜 일상 속에서 어떻게 실천될 수 있나요?", "팔만대장경에서 말하는 '진정한 행복'은 무엇인가요?", "경전에서 강조하는 자비와 공감의 구체적인 수행법을 가르쳐주세요."]
            },
            saju: {
                intro: "타고난 기운과 지혜를 결합하여 삶의 길을 풀어드리는 **사주 명리 모드**입니다. 생년월일시와 함께 궁금한 운세를 말씀해 주세요. 🔮",
                questions: ["저의 사주에 담긴 잠재력과 불교적 보완법이 궁금합니다.", "현재 겪고 있는 운의 흐름을 지혜롭게 헤쳐나갈 조언을 부탁드려요.", "타고난 기운을 다듬어 내면의 평화를 찾는 일상적 수행이 있을까요?", "재물이나 명예보다 더 큰 복덕을 쌓는 삶의 태도는 무엇인가요?"]
            },
            personality: {
                intro: "🔯 **MBTI/별자리 맞춤 지혜 모드**입니다.\n\n당신의 성격 유형과 타고난 기운을 팔만대장경의 지혜와 연결하여, 오직 당신만을 위한 깊은 통찰과 수행의 길을 안내해 드립니다. 🔯",
                questions: ["제 성격 유형(MBTI)의 강점이 보살의 덕목과 어떻게 연결되나요?", "내 성향에 꼭 맞는 명상법이나 마음챙김 도구는 무엇일까요?", "인간관계의 갈등을 저의 기질을 활용해 지혜롭게 푸는 법이 궁금해요.", "별자리의 기운이 불교적 인연법과 어떤 관계가 있나요?"]
            }
        }
    },
    en: {
        subtitle: "Mind Care with Buddha's Wisdom",
        newChat: "New Session",
        counselMode: "Select Mode",
        counseling: "Counseling",
        sutraQna: "Sutra Q&A",
        saju: "Saju Astrology",
        infoTitle: "🪷 Guidance",
        infoText: "Providing comfort and peace of mind through the wisdom of the Tripitaka.",
        voiceBtn: "🎙️ Voice coming soon",
        sutrasBadge: "📖 Wisdom Counseling",
        statusReady: "Ready to listen",
        inputPlaceholder: "Share the story in your mind...",
        inputHint: "Enter to send · Shift+Enter for new line · Wisdom Counseling",
        setupTitle: "Welcome to MindBuddhi",
        setupLangTitle: "🌐 Select Language",
        setupLangDesc: "Please choose your preferred language.",
        setupDesc: "<strong>Buddhi</strong> is a Sanskrit word meaning intellect, intelligence, and high-order wisdom. It goes beyond simple knowledge to signify intuitive insight that penetrates the true essence of things and represents true awakening.",
        setupVoiceTitle: "🎙️ Counsel Voice Selection",
        setupVoiceDesc: "Please select a voice to soothe your mind.",
        setupVoiceOption1: "Buddhi",
        setupVoiceTag1: "Experimental",
        setupVoiceOption2: "AI Voice",
        setupVoiceTag2: "Coming soon",
        setupStartBtn: "Begin the Journey of Wisdom",
        consentText: "I agree to the collection and use of consultation data for better service.",
        mbti_infj: "Advocate (INFJ)",
        loadingStatus1: "Listening to your heart...",
        loadingStatus2: "Finding wisdom in the Tripitaka...",
        loadingStatus3: "Polishing the words of wisdom...",
        tracks: {
            counseling: {
                intro: "Hello. I am **MindBuddhi**, an AI emotional support service offering peace based on the teachings of the Tripitaka.\n\nWhat is in your heart today? Whether it is anxiety, loneliness, or sorrow, feel free to share. We will look at it together with the wisdom of the sages. 🙏",
                questions: ["I want to know the Buddha's teachings to overcome recurring anxiety.", "How should I heal the stress and wounds from interpersonal relationships?", "Please give me wisdom to manage the fear of an uncertain future.", "How can I let go of past regrets and live deeply in the present?"]
            },
            inquiry: {
                intro: "This is the **Sutra Q&A mode** where we find answers in the vast wisdom of the Tripitaka. Do you have any questions about Buddha's teachings? 📖",
                questions: ["Tell me about the fundamental cause and solution of suffering in the Madhyama Agama.", "How can the Eightfold Path be practiced in the busy daily life of modern people?", "What is 'true happiness' as described in the Tripitaka Koreana?", "Please teach me specific practices of compassion and empathy emphasized in the scriptures."]
            },
            saju: {
                intro: "This is the **Saju Astrology mode** that unravels the path of life by combining innate energy and wisdom. Please tell me your fortune questions along with your birth date and time. 🔮",
                questions: ["I'm curious about the potential in my Saju and ways to complement it with Buddhist wisdom.", "Please give me advice to wisely navigate through my current life fortune.", "Are there daily practices to refine my innate energy and find inner peace?", "What life attitude allows one to accumulate more merit than wealth or fame?"]
            },
            personality: {
                intro: "🔯 **Personality-Based Wisdom Mode**\n\nI will connect your personality type (MBTI/Zodiac) with the timeless teachings of the Tripitaka, offering you a truly personal spiritual experience. 🔯",
                questions: ["How do the strengths of my MBTI type connect to the virtues of a Bodhisattva?", "What meditation techniques or mindfulness tools perfectly suit my temperament?", "How can I wisely resolve relationship conflicts using my personality traits?", "What is the relationship between zodiac energy and the Buddhist law of connection?"]
            }
        }
    }
};

let TRACK_DATA = i18n.ko.tracks;

// ── Profile helper: persist MBTI/Zodiac ──────────────────────
function setProfile(mbti, zodiac) {
    if (mbti !== null) {
        currentProfile.mbti = mbti || null;
        if (mbti) localStorage.setItem('profile_mbti', mbti);
        else localStorage.removeItem('profile_mbti');
    }
    if (zodiac !== null) {
        currentProfile.zodiac = zodiac || null;
        if (zodiac) localStorage.setItem('profile_zodiac', zodiac);
        else localStorage.removeItem('profile_zodiac');
    }
    updateProfileBadge();
}

function updateProfileBadge() {
    const badge = document.getElementById('profileBadge');
    if (!badge) return;
    const parts = [];
    if (currentProfile.mbti) parts.push(currentProfile.mbti);
    if (currentProfile.zodiac) parts.push(currentProfile.zodiac);
    if (parts.length) {
        badge.textContent = '🔯 ' + parts.join(' · ');
        badge.style.display = 'block';
    } else {
        badge.style.display = 'none';
    }
}

function toggleLanguage() {
    currentLang = currentLang === 'ko' ? 'en' : 'ko';
    localStorage.setItem('lang', currentLang);
    applyLanguage();
    updateModalLangButtons();
}

function changeLangFromModal(lang) {
    if (currentLang === lang) return;
    currentLang = lang;
    localStorage.setItem('lang', currentLang);
    applyLanguage();
    updateModalLangButtons();
}

function updateModalLangButtons() {
    const koBtn = document.getElementById('lang-opt-ko');
    const enBtn = document.getElementById('lang-opt-en');
    if (koBtn) koBtn.classList.toggle('active', currentLang === 'ko');
    if (enBtn) enBtn.classList.toggle('active', currentLang === 'en');
}

function selectVoice(voice) {
    currentVoice = voice || 'buddi';
    localStorage.setItem('mindbuddi_voice', currentVoice);
    updateVoiceSelection();
}

function updateVoiceSelection() {
    document.querySelectorAll('input[name="voiceSelect"]').forEach(input => {
        const isSelected = input.value === currentVoice;
        input.checked = isSelected;
        const option = input.closest('.voice-option');
        if (option) option.classList.toggle('active', isSelected);
    });
}

function applyLanguage() {
    TRACK_DATA = i18n[currentLang].tracks;

    // Update button text
    const langBtn = document.getElementById('langToggleBtn');
    if (langBtn) langBtn.textContent = currentLang === 'ko' ? 'EN' : 'KO';
    
    // Process text nodes
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (i18n[currentLang][key]) {
            el.innerHTML = i18n[currentLang][key]; // innerHTML for strong tags
        }
    });

    // Process placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (i18n[currentLang][key]) {
            el.placeholder = i18n[currentLang][key];
        }
    });

    // Refresh dynamic welcome messages and prompts
    if (history.length === 0) {
        // Just refresh the prompts if we are at the start
        updateWelcomeMessage(currentTrack);
    } else {
        // Update all quick-prompts in the DOM if we already have history
        document.querySelectorAll('.quick-prompts').forEach(el => {
            el.innerHTML = TRACK_DATA[currentTrack].questions.map(q =>
                `<button class="quick-btn" onclick="sendQuick(this.getAttribute('data-q'))" data-q="${escapeAttr(q)}">${escapeHtml(q)}</button>`
            ).join('');
        });
    }
}


// ── View Mode Toggle Logic ──────────────────────
const viewModeToggleBtn = document.getElementById('viewModeToggle');
const viewportMeta = document.querySelector('meta[name="viewport"]');

function isSmallViewport() {
    return Math.min(window.screen.width, window.screen.height) <= 768;
}

function getStoredViewMode() {
    return sessionStorage.getItem(VIEW_MODE_KEY) === 'desktop' ? 'desktop' : 'mobile';
}

function updateViewModeButton() {
    if (!viewModeToggleBtn) return;
    const isDesktopMode = document.body.classList.contains('force-desktop-mode');
    viewModeToggleBtn.textContent = isDesktopMode ? '모바일 버전' : 'PC 버전';
    viewModeToggleBtn.setAttribute('aria-pressed', String(isDesktopMode));
}

function updateViewportMode(forceDesktop) {
    if (!viewportMeta) return;
    if (forceDesktop) {
        const screenWidth = Math.min(window.screen.width, window.screen.height) || window.innerWidth || DESKTOP_VIEWPORT_WIDTH;
        const initialScale = Math.min(1, Math.max(0.22, screenWidth / DESKTOP_VIEWPORT_WIDTH));
        viewportMeta.setAttribute(
            'content',
            `width=${DESKTOP_VIEWPORT_WIDTH}, initial-scale=${initialScale.toFixed(3)}, maximum-scale=5, user-scalable=yes`
        );
        return;
    }
    viewportMeta.setAttribute('content', MOBILE_VIEWPORT_CONTENT);
}

function applyViewMode(mode) {
    const forceDesktop = isSmallViewport() && mode === 'desktop';
    document.documentElement.classList.toggle('force-desktop-mode', forceDesktop);
    document.body.classList.toggle('force-desktop-mode', forceDesktop);
    updateViewportMode(forceDesktop);
    updateViewModeButton();
}

function syncViewMode() {
    if (isSmallViewport()) {
        applyViewMode(getStoredViewMode());
    } else {
        document.documentElement.classList.remove('force-desktop-mode');
        document.body.classList.remove('force-desktop-mode');
        updateViewModeButton();
    }
}

function toggleViewMode() {
    if (!isSmallViewport()) return;
    const nextMode = document.body.classList.contains('force-desktop-mode') ? 'mobile' : 'desktop';
    sessionStorage.setItem(VIEW_MODE_KEY, nextMode);
    applyViewMode(nextMode);
}



const messagesArea = document.getElementById('messagesArea');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');

/** ── Track Selection Logic ── */
function setTrack(mode, showModal = true) {
    if (currentTrack === mode && mode !== 'personality') return;
    
    // If switching to personality track AND showModal is true, show Step 2 (MBTI selection)
    if (mode === 'personality' && showModal) {
        openSetupModal(2);
    }

    currentTrack = mode;
    ['counseling', 'inquiry', 'saju', 'personality'].forEach(t => {
        const btn = document.getElementById(`track-${t}`);
        if (btn) btn.classList.toggle('active', t === mode);
    });

    updateWelcomeMessage(mode);
    newChat();
}

function updateWelcomeMessage(mode) {
    const welcomeMsg = document.getElementById('welcomeMsg');
    if (!welcomeMsg) return;

    const data = TRACK_DATA[mode] || TRACK_DATA.counseling;
    const introArea = welcomeMsg.querySelector('.bubble');
    const promptArea = welcomeMsg.querySelector('.quick-prompts');

    if (introArea) {
        if (window.marked) introArea.innerHTML = window.marked.parse(data.intro);
        else introArea.innerHTML = `<p>${data.intro}</p>`;
    }

    if (promptArea) {
        promptArea.innerHTML = data.questions.map(q =>
            `<button class="quick-btn" onclick="sendQuick(this.getAttribute('data-q'))" data-q="${escapeAttr(q)}">${escapeHtml(q)}</button>`
        ).join('');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Clear all storage on refresh as requested for "fresh start" every time
    localStorage.clear();
    sessionStorage.clear();
    
    // Set default language to Korean if cleared or not set
    currentLang = 'ko';
    currentVoice = 'buddi';
    localStorage.setItem('lang', 'ko');
    localStorage.setItem('mindbuddi_voice', currentVoice);
    
    console.log("MindBuddhi — Wisdom Counseling Initialized (Storage Cleared)");
    
    applyLanguage(); // Initial language setup
    updateModalLangButtons();
    updateVoiceSelection();
    updateProfileBadge(); // Show saved profile if any
    updateStartButtonState(); // Initialize button state
    
    // Allow badge to reopen setup
    const badge = document.getElementById('profileBadge');
    if (badge) {
        badge.addEventListener('click', () => {
            openSetupModal(2);
        });
    }

    // ── Setup Modal Multi-step Logic ──
    const setupModal = document.getElementById('setupModal');
    
    // Only show Step 1 (Welcome & Consent) on first initial load
    if (!localStorage.getItem('mindbuddi-setup-done')) {
        openSetupModal(1);
    }

    syncViewMode();
    if (!isSmallViewport()) {
        userInput.focus();
    }
    updateWelcomeMessage('counseling');
});

function showSetupStep(step) {
    [1, 2, 3].forEach(n => {
        const el = document.getElementById(`setupStep${n}`);
        if (el) el.style.display = n === step ? 'block' : 'none';
    });
}

function openSetupModal(step = 1) {
    const modal = document.getElementById('setupModal');
    if (!modal) return;
    if (modal._closeTimer) {
        clearTimeout(modal._closeTimer);
        modal._closeTimer = null;
    }
    showSetupStep(step);
    modal.style.display = 'flex';
    modal.style.opacity = '1';
    modal.style.pointerEvents = 'auto';
}

function selectMbti(type) {
    document.querySelectorAll('.mbti-card').forEach(btn => {
        btn.classList.toggle('selected', btn.dataset.mbti === type);
    });
    currentProfile.mbti = type;
    localStorage.setItem('profile_mbti', type);
    const nextBtn = document.getElementById('mbtiNextBtn');
    if (nextBtn) nextBtn.disabled = false;
}

function selectZodiac(sign) {
    document.querySelectorAll('.zodiac-card').forEach(btn => {
        const attrOnclick = btn.getAttribute('onclick') || '';
        btn.classList.toggle('selected', attrOnclick.includes(`'${sign}'`));
    });
    currentProfile.zodiac = sign;
    localStorage.setItem('profile_zodiac', sign);
    const nextBtn = document.getElementById('zodiacNextBtn');
    if (nextBtn) nextBtn.disabled = false;
}

function completeSetup() {
    updateProfileBadge();
    closeSetupModal();
    // Auto-switch to personality track without showing modal again
    if (currentProfile.mbti || currentProfile.zodiac) {
        setTrack('personality', false);
    }
}

function closeSetupModal() {
    const modal = document.getElementById('setupModal');
    const checkbox = document.getElementById('consentCheckbox');
    
    if (checkbox && !checkbox.checked) {
        alert(currentLang === 'ko' ? "상담 데이터 수집에 동의해 주세요." : "Please agree to the data collection.");
        return;
    }

    if (modal) {
        modal.style.opacity = '0';
        modal.style.pointerEvents = 'none';
        modal.style.display = 'none';
    }
    // Set a flag in localStorage so it doesn't show again
    localStorage.setItem('mindbuddi-setup-done', 'true');
    userInput.focus();
}

function updateStartButtonState() {
    const checkbox = document.getElementById('consentCheckbox');
    const btn = document.getElementById('finalStartBtn');
    if (checkbox && btn) {
        if (checkbox.checked) {
            btn.disabled = false;
            btn.style.opacity = '1';
            btn.style.cursor = 'pointer';
            btn.classList.remove('disabled');
        } else {
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
            btn.classList.add('disabled');
        }
    }
}

window.addEventListener('resize', syncViewMode);

function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

function sendQuick(text) {
    console.log("Quick Prompt Clicked:", text);
    userInput.value = text;
    autoResize(userInput);
    sendMessage();
}

function newChat() {
    history = [];
    const msgs = messagesArea.querySelectorAll('.message:not(#welcomeMsg), .typing-indicator');
    msgs.forEach(m => m.remove());

    // Always refresh welcome message on new chat to keep prompts consistent
    updateWelcomeMessage(currentTrack);

    userInput.value = '';
    autoResize(userInput);
    userInput.focus();
}

async function sendMessage() {
    const text = userInput.value.trim();
    console.log("Attempting to send message:", text);
    if (!text || isLoading) {
        console.log("Send blocked: empty text or currently loading (isLoading=" + isLoading + ")");
        return;
    }

    appendUserMessage(text);
    history.push({ role: 'user', content: text });

    userInput.value = '';
    userInput.style.height = 'auto';
    setLoading(true);

    const typingEl = appendTypingIndicator();

    try {
        const res = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                history: history.slice(-12),
                track: currentTrack,
                mbti: currentProfile.mbti || undefined,
                zodiac: currentProfile.zodiac || undefined,
                lang: currentLang
            }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        if (typingEl._loadingInterval) clearInterval(typingEl._loadingInterval);
        typingEl.remove();

        appendBotMessage(data.answer, data.sources || [], data.images || []);
        history.push({ role: 'assistant', content: data.answer });

    } catch (err) {
        if (typingEl._loadingInterval) clearInterval(typingEl._loadingInterval);
        typingEl.remove();
        appendErrorMessage(err.message);
    } finally {
        setLoading(false);
    }
}

function appendUserMessage(text) {
    const div = document.createElement('div');
    div.className = 'message user-message';
    div.innerHTML = `
    <div class="avatar">🙏</div>
    <div class="message-body"><div class="bubble"><p>${escapeHtml(text)}</p></div></div>`;
    messagesArea.appendChild(div);
    scrollBottom();
}

function appendBotMessage(answer, sources, images) {
    const div = document.createElement('div');
    div.className = 'message bot-message';

    let formattedAnswer = answer;
    if (window.marked) {
        formattedAnswer = window.marked.parse(answer);
    } else {
        formattedAnswer = escapeHtml(answer).replace(/\n/g, '<br>');
    }

    const imgHintText = currentLang === 'en' ? "💡 Click on the image to view the translation." : "💡 사진을 클릭하여 원문 해석을 확인하세요.";
    let imagesHtml = '';
    if (images && images.length > 0) {
        imagesHtml = `<div class="images-gallery">` + images.map(img =>
            `<div class="img-card" 
                  data-url="${escapeAttr(img.url)}" 
                  data-alt="${escapeAttr(img.alt)}" 
                  data-trans="${escapeAttr(img.translation || '')}" 
                  data-highlights='${escapeAttr(JSON.stringify(img.highlights || []))}'
                  onclick="openModalFromEl(this)">
                <img src="${escapeAttr(img.url)}" alt="${escapeAttr(img.alt)}" />
                <div class="img-label">${escapeHtml(img.alt)}</div>
            </div>`
        ).join('') + `</div><div class="img-hint">${imgHintText}</div>`;
    }

    const sourceTitleText = currentLang === 'en' ? "✨ Source of Wisdom" : "✨ 지혜의 출처";
    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        const uniqueLabels = [...new Set(sources.map(s => s.label))];
        const tags = uniqueLabels.map(label => `<span class="source-tag">📍 ${escapeHtml(label)}</span>`).join('');
        sourcesHtml = `<div class="sources-container"><div class="sources-title">${sourceTitleText}</div><div class="sources-list">${tags}</div></div>`;
    }

    const voiceText = extractFirstAnswerSection(answer);
    const voiceLabel = currentLang === 'en' ? 'Play voice' : '\uc74c\uc131 \ucd9c\ub825';
    const voiceHtml = voiceText
        ? `<button class="voice-output-btn" type="button" data-voice-text="${escapeAttr(voiceText)}" onclick="playAnswerVoice(this)" title="${voiceLabel}" aria-label="${voiceLabel}">
            <svg class="voice-ring" viewBox="0 0 36 36" aria-hidden="true">
              <circle class="voice-ring-track" cx="18" cy="18" r="15.5"></circle>
              <circle class="voice-ring-progress" cx="18" cy="18" r="15.5"></circle>
            </svg>
            <span class="voice-icon">🎙️</span>
          </button>`
        : '';

    // Feedback
    const feedbackPrompt = currentLang === 'en' ? "Was this helpful?" : "도움이 되었나요?";
    const feedbackHtml = `<div class="feedback-area"><span class="feedback-text">${feedbackPrompt}</span><div class="feedback-btns"><button class="feedback-btn" onclick="handleFeedback(this, 'up')">👍</button><button class="feedback-btn" onclick="handleFeedback(this, 'down')">👎</button></div></div>`;

    // Suggestions (based on Track Data)
    const suggestionsHtml = `<div class="quick-prompts">` + TRACK_DATA[currentTrack].questions.map(q =>
        `<button class="quick-btn" onclick="sendQuick(this.getAttribute('data-q'))" data-q="${escapeAttr(q)}">${escapeHtml(q)}</button>`
    ).join('') + `</div>`;

    div.innerHTML = `
    <img src="/static/logo.png" class="avatar" alt="MB">
    <div class="message-body">
      <div class="bubble markdown-body">${formattedAnswer}${imagesHtml}${sourcesHtml}${feedbackHtml}${voiceHtml}</div>
      ${suggestionsHtml}
    </div>`;

    messagesArea.appendChild(div);
    scrollBottom();
    return { div };
}

function extractFirstAnswerSection(answer) {
    if (!answer) return '';
    const lines = String(answer).split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    if (!lines.length) return '';

    let start = lines.findIndex(line => /^#{1,4}\s+/.test(line) || /^[^\s].{0,40}$/.test(line));
    if (start < 0) start = 0;

    const picked = [];
    for (let i = start; i < lines.length; i++) {
        const line = lines[i];
        const isHeading = /^#{1,4}\s+/.test(line) || /^[^\s].{0,40}$/.test(line);
        if (i === start && isHeading) continue;
        if (i > start && isHeading) break;
        if (/!\[|\]\(|^\|/.test(line)) continue;
        picked.push(line);
        if (picked.length >= 3) break;
    }

    return picked
        .join(' ')
        .replace(/^#{1,4}\s+/g, '')
        .replace(/\*\*|__|[*_`>#-]/g, '')
        .replace(/\[[^\]]+\]\([^)]+\)/g, '')
        .replace(/\s+/g, ' ')
        .trim()
        .slice(0, 700);
}

async function playAnswerVoice(btn) {
    const text = btn.getAttribute('data-voice-text') || '';
    if (!text) return;

    if (activeAudio && !activeAudio.paused) {
        activeAudio.pause();
        activeAudio = null;
        stopVoiceProgress(btn);
        btn.classList.remove('playing', 'loading', 'error');
        return;
    }

    if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
        activeUtterance = null;
        stopVoiceProgress(btn);
        btn.classList.remove('playing', 'loading', 'error');
        return;
    }

    btn.classList.remove('error');
    if (currentVoice === 'buddi') {
        btn.classList.add('loading');
        startVoiceProgress(btn, text);
        btn.title = currentLang === 'en' ? 'Generating voice...' : '\uc74c\uc131 \uc0dd\uc131 \uc911...';
        try {
            const response = await fetch(`${API_BASE}/api/tts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text,
                    voice: currentVoice,
                    language: currentLang === 'en' ? 'en' : 'ko'
                })
            });
            if (!response.ok) throw new Error(`XTTS request failed: ${response.status}`);
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            activeAudio = audio;
            stopVoiceProgress(btn, 100);
            btn.classList.remove('loading');
            btn.classList.add('playing');
            btn.title = currentLang === 'en' ? 'Stop voice' : '\uc74c\uc131 \uc815\uc9c0';
            audio.onended = () => {
                URL.revokeObjectURL(url);
                activeAudio = null;
                stopVoiceProgress(btn);
                btn.classList.remove('playing', 'loading', 'error');
                btn.title = currentLang === 'en' ? 'Play voice' : '\uc74c\uc131 \ucd9c\ub825';
            };
            audio.onerror = () => {
                URL.revokeObjectURL(url);
                activeAudio = null;
                stopVoiceProgress(btn);
                btn.classList.remove('playing', 'loading');
                btn.classList.add('error');
                btn.title = currentLang === 'en' ? 'Voice playback failed' : '\uc74c\uc131 \uc7ac\uc0dd \uc2e4\ud328';
            };
            await audio.play();
            return;
        } catch (error) {
            console.warn('Buddhi XTTS unavailable.', error);
            stopVoiceProgress(btn);
            btn.classList.remove('loading', 'playing');
            btn.classList.add('error');
            btn.title = currentLang === 'en' ? 'Buddhi voice failed. Try again.' : '\ubd80\ub514 \uc74c\uc131 \uc0dd\uc131 \uc2e4\ud328. \ub2e4\uc2dc \uc2dc\ub3c4\ud574\uc8fc\uc138\uc694.';
            return;
        }
    }

    btn.classList.add('playing');
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = currentLang === 'en' ? 'en-US' : 'ko-KR';
    utterance.rate = 0.92;
    utterance.pitch = currentVoice === 'buddi' ? 0.88 : 1;
    utterance.onend = () => btn.classList.remove('playing');
    utterance.onerror = () => btn.classList.remove('playing');
    activeUtterance = utterance;
    window.speechSynthesis.speak(utterance);
}

function startVoiceProgress(btn, text) {
    stopVoiceProgress(btn);
    const estimatedMs = Math.min(45000, Math.max(14000, (text || '').length * 85));
    const startedAt = Date.now();
    btn.style.setProperty('--voice-progress', '0deg');
    activeVoiceProgressTimer = setInterval(() => {
        const elapsed = Date.now() - startedAt;
        const progress = Math.min(92, (elapsed / estimatedMs) * 100);
        btn.style.setProperty('--voice-progress', `${progress * 3.6}deg`);
        btn.style.setProperty('--voice-ring-offset', `${97.39 - (97.39 * progress / 100)}`);
    }, 160);
}

function stopVoiceProgress(btn, finalProgress = 0) {
    if (activeVoiceProgressTimer) {
        clearInterval(activeVoiceProgressTimer);
        activeVoiceProgressTimer = null;
    }
    if (!btn) return;
    if (finalProgress) {
        btn.style.setProperty('--voice-progress', `${finalProgress * 3.6}deg`);
        btn.style.setProperty('--voice-ring-offset', '0');
    } else {
        btn.style.removeProperty('--voice-progress');
        btn.style.removeProperty('--voice-ring-offset');
    }
}

function handleFeedback(btn, type) {
    const p = btn.closest('.feedback-btns');
    p.querySelectorAll('.feedback-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    let toast = document.createElement('div');
    toast.style = "position:fixed; bottom:50px; left:50%; transform:translateX(-50%); background:rgba(0,0,0,0.8); color:white; padding:10px 20px; border-radius:20px; font-size:13px; z-index:9999;";
    toast.textContent = type === 'up' ? "감사합니다! 🙏" : "불편을 드려 죄송합니다.";
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2500);
}

// ── Sentence-based Highlighting Logic Removed (Moved to Backend) ──

function openModalFromEl(el) {
    const url = el.getAttribute('data-url');
    const trans = el.getAttribute('data-trans');
    let highlights = [];
    try {
        highlights = JSON.parse(el.getAttribute('data-highlights') || '[]');
    } catch(e) {}
    openModal(url, trans, highlights);
}

function openModal(url, translation, highlights = []) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    
    // Apply highlights to translation text
    let highlightedText = translation;
    if (highlights && highlights.length > 0) {
        highlights.forEach(h => {
            if (h.trim()) {
                // Use split/join to replace all occurrences while being safe with strings
                highlightedText = highlightedText.split(h).join(`<mark>${h}</mark>`);
            }
        });
    }

    const modalTitleText = currentLang === 'en' ? "📖 Scripture Analysis (Split-View)" : "📖 경전 분석 (Split-View)";
    const splitTitleText = currentLang === 'en' ? "📜 Wisdom's Interpretation" : "📜 지혜의 해석";
    const loadingText = currentLang === 'en' ? "Loading interpretation..." : "해석을 불러오는 중입니다.";
    const highlightNote = currentLang === 'en' ? "※ The highlighted sentence is the teaching most closely related in meaning to the answer." : "※ 하이라이트된 문장은 답변과 의미적으로 가장 밀접한 가르침입니다.";

    overlay.innerHTML = `
    <div class="modal-content">
      <div class="modal-header-tabs">
        <button class="modal-tab-btn active">${modalTitleText}</button>
      </div>
      <div class="modal-body-content">
        <div class="modal-split-view">
          <div class="modal-left"><img src="${escapeAttr(url)}" /></div>
          <div class="modal-right">
             <h3 style="margin-bottom:20px; font-family:'Noto Serif KR', serif; color:var(--primary-darker);">${splitTitleText}</h3>
             <div class="trans-text">${highlightedText || loadingText}</div>
             <p style="margin-top:30px; font-size:13px; color:var(--text-muted); border-top:1px solid #eee; padding-top:20px;">${highlightNote}</p>
          </div>
        </div>
      </div>
      <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">✕</button>
    </div>`;
    document.body.appendChild(overlay);
}

function appendTypingIndicator() {
    const div = document.createElement('div');
    div.className = 'typing-indicator';
    div.innerHTML = `
    <img src="/static/logo.png" class="avatar" alt="MB" style="width:38px;height:38px;flex-shrink:0;">
    <div class="loading-status-box">
      <div class="loading-status-text" id="loadingStatusText">${i18n[currentLang].loadingStatus1}</div>
      <div class="loading-progress-container">
        <div class="loading-progress-bar" id="loadingProgressBar" style="width: 5%;"></div>
      </div>
    </div>`;
    messagesArea.appendChild(div);
    scrollBottom();
    
    const bar = div.querySelector('#loadingProgressBar');
    const text = div.querySelector('#loadingStatusText');
    let progress = 5;
    
    const statuses = [
        i18n[currentLang].loadingStatus1,
        i18n[currentLang].loadingStatus2,
        i18n[currentLang].loadingStatus3
    ];
    let statusIndex = 0;
    
    // Faster interval for smoother "filling" animation
    const interval = setInterval(() => {
        progress += Math.random() * 1.5 + 0.5; // Smaller chunks, more frequent
        if (progress > 98) progress = 98;
        if (bar) bar.style.width = progress + '%';
        
        if (progress > 35 && statusIndex === 0) {
            statusIndex = 1;
            if (text) text.textContent = statuses[1];
        } else if (progress > 75 && statusIndex === 1) {
            statusIndex = 2;
            if (text) text.textContent = statuses[2];
        }
    }, 150);
    
    div._loadingInterval = interval;
    
    return div;
}

function appendErrorMessage(msg) {
    const div = document.createElement('div');
    div.className = 'message bot-message';
    div.innerHTML = `<img src="static/logo.png" class="avatar"><div class="message-body"><div class="bubble"><p style="color:red">오류: ${escapeHtml(msg)}</p></div></div>`;
    messagesArea.appendChild(div);
    scrollBottom();
}

function setLoading(v) { isLoading = v; sendBtn.disabled = v; userInput.disabled = v; }
function scrollBottom() { setTimeout(() => { messagesArea.scrollTop = messagesArea.scrollHeight; }, 50); }
function escapeHtml(str) { const div = document.createElement('div'); div.textContent = str; return div.innerHTML; }
function escapeAttr(str) { return String(str).replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }



