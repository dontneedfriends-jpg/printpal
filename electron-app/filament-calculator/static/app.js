function setCookie(name, value) {
    document.cookie = name + '=' + value + '; path=/; max-age=31536000';
}
function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
}

function showToast(message, type) {
    type = type || 'info';
    var c = document.getElementById('toast-container');
    if (!c) return;
    var t = document.createElement('div');
    t.className = 'toast toast-' + type;
    t.textContent = message;
    c.appendChild(t);
    setTimeout(function() { t.classList.add('toast-out'); setTimeout(function() { t.remove(); }, 300); }, 5000);
}

function showUndoToast(message, undoCallback) {
    var c = document.getElementById('toast-container');
    if (!c) return;
    var toast = document.createElement('div');
    toast.className = 'toast toast-undo';
    
    var msgSpan = document.createElement('span');
    msgSpan.className = 'toast-undo-msg';
    msgSpan.textContent = message;
    
    var undoBtn = document.createElement('button');
    undoBtn.className = 'toast-undo-btn';
    undoBtn.title = LANG === 'ru' ? 'Отменить' : LANG === 'es' ? 'Deshacer' : 'Undo';
    undoBtn.innerHTML = '&#8635;';
    
    var countdownSpan = document.createElement('span');
    countdownSpan.className = 'toast-countdown';
    
    toast.appendChild(msgSpan);
    toast.appendChild(countdownSpan);
    toast.appendChild(undoBtn);
    c.appendChild(toast);
    
    var countdown = 5;
    countdownSpan.textContent = countdown;
    
    var timer = setInterval(function() {
        countdown--;
        if (countdown > 0) {
            countdownSpan.textContent = countdown;
        } else {
            clearInterval(timer);
            toast.classList.add('toast-out');
            setTimeout(function() { toast.remove(); }, 300);
        }
    }, 1000);
    
    undoBtn.onclick = function() {
        clearInterval(timer);
        undoCallback();
        toast.classList.add('toast-out');
        setTimeout(function() { toast.remove(); }, 300);
    };
}

function appConfirm(text, title) {
    return new Promise(function(resolve) {
        var m = document.getElementById('global-confirm');
        var t = document.getElementById('confirm-text');
        var ti = document.getElementById('confirm-title');
        var ok = document.getElementById('confirm-ok');
        var cancel = document.getElementById('confirm-cancel');
        if (t) t.textContent = text || 'Confirm?';
        if (ti) ti.textContent = title || 'Confirm';
        m.style.display = 'flex';
        function cleanup() { m.style.display = 'none'; ok.removeEventListener('click', onOk); cancel.removeEventListener('click', onCancel); }
        function onOk() { cleanup(); resolve(true); }
        function onCancel() { cleanup(); resolve(false); }
        ok.addEventListener('click', onOk);
        cancel.addEventListener('click', onCancel);
    });
}

const theme = getCookie('theme') || localStorage.getItem('theme') || 'light';
const preset = getCookie('preset') || localStorage.getItem('preset') || 'modern';
const glass = getCookie('glass') !== null ? getCookie('glass') : (localStorage.getItem('glass') || '1');

setCookie('theme', theme);
setCookie('preset', preset);
setCookie('glass', glass);
setCookie('lang', LANG);
localStorage.setItem('theme', theme);
localStorage.setItem('preset', preset);
localStorage.setItem('glass', glass);
localStorage.setItem('lang', LANG);

document.documentElement.setAttribute('data-theme', theme);
document.documentElement.setAttribute('data-preset', preset);
document.documentElement.setAttribute('data-glass', glass);
updateThemeIcon(theme);

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    setCookie('theme', next);
    localStorage.setItem('theme', next);
    updateThemeIcon(next);
    setTimeout(() => location.reload(), 300);
}

function updateThemeIcon(theme) {
    const btn = document.querySelector('.theme-toggle');
    if (btn) btn.textContent = theme === 'dark' ? '☀️' : '🌙';
}

if (window.electronAPI) {
    const observer = new MutationObserver(() => {
        const iconMax = document.querySelector('.icon-maximize');
        const iconRestore = document.querySelector('.icon-restore');
        if (iconMax && iconRestore) {
            const isMax = window.matchMedia('(display-mode: fullscreen)').matches;
            iconMax.style.display = isMax ? 'none' : 'block';
            iconRestore.style.display = isMax ? 'block' : 'none';
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
}

(function() {
    const saved = getCookie('tab_order') || localStorage.getItem('tab_order') || '';
    if (!saved) return;
    const order = saved.split(',');
    const nav = document.getElementById('nav-links');
    if (!nav) return;
    const links = Array.from(nav.querySelectorAll('a[data-endpoint]'));
    const toggle = nav.querySelector('.theme-toggle');
    order.forEach(function(ep) {
        const link = links.find(function(el) { return el.dataset.endpoint === ep; });
        if (link) nav.insertBefore(link, toggle);
    });
})();

var easterEgg = { pos: 0, code: ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'] };
document.addEventListener('keydown', function(e) {
    var key = e.key;
    if (key === easterEgg.code[easterEgg.pos]) {
        easterEgg.pos++;
        if (easterEgg.pos >= easterEgg.code.length) {
            var logo = document.querySelector('.titlebar-title');
            if (logo) {
                logo.textContent = '🎉 PrintPAL 🎉';
                logo.style.animation = 'spin 1s ease';
                showToast('🎉 YOU FOUND THE EASTER EGG! 🎉', 'success');
            }
            easterEgg.pos = 0;
        }
    } else {
        easterEgg.pos = 0;
    }
});

document.querySelector('.titlebar-title')?.addEventListener('click', function() {
    if (Math.random() < 0.1) {
        showToast('🖨️ Приятной печати! 🖨️', 'success');
    }
});
