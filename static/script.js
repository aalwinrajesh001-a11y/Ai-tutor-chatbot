/**
 * LearnBot — script.js
 * Handles: chat, markdown rendering, quiz interactions, UI polish
 */

// ─────────────────────────────────────────────
// Simple Markdown → HTML renderer
// ─────────────────────────────────────────────
function renderMarkdown(text) {
    if (!text) return '';

    let html = text
        // Headings
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h2>$1</h2>')
        // Bold
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Horizontal rule
        .replace(/^---$/gm, '<hr>')
        // Unordered list
        .replace(/^\- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
        // Ordered list (simple)
        .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
        // Paragraphs: split on double newlines
        .split(/\n{2,}/)
        .map(block => {
            block = block.trim();
            if (!block) return '';
            if (/^<(h[1-6]|ul|ol|li|hr)/.test(block)) return block;
            return `<p>${block.replace(/\n/g, '<br>')}</p>`;
        })
        .join('\n');

    return html;
}

// Render all bot messages that have data-markdown attribute
function renderAllMarkdown() {
    document.querySelectorAll('[data-markdown]').forEach(el => {
        const raw = el.getAttribute('data-markdown');
        el.innerHTML = renderMarkdown(raw);
        el.removeAttribute('data-markdown');
    });
}

// ─────────────────────────────────────────────
// Chat Functions
// ─────────────────────────────────────────────

// Add a message bubble to the chat
function appendMessage(role, text) {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    const wrapper = document.createElement('div');
    wrapper.className = `message ${role === 'user' ? 'user-message' : 'bot-message'}`;

    if (role === 'bot') {
        wrapper.innerHTML = `
            <div class="msg-avatar">⬡</div>
            <div class="msg-bubble">${renderMarkdown(text)}</div>
        `;
    } else {
        wrapper.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
    }

    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
    return wrapper;
}

// Escape HTML to prevent XSS in user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show/hide the typing indicator
function showTyping(show) {
    const el = document.getElementById('typingIndicator');
    if (el) el.style.display = show ? 'flex' : 'none';
    if (show) {
        const container = document.getElementById('chatMessages');
        if (container) container.scrollTop = container.scrollHeight;
    }
}

// Send a message from the input box
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    if (!input) return;

    const text = input.value.trim();
    if (!text) return;

    // Disable input while waiting
    input.value = '';
    input.disabled = true;
    if (sendBtn) sendBtn.disabled = true;
    input.style.height = 'auto';

    // Hide suggestion bar after first message
    const suggBar = document.getElementById('suggestionBar');
    if (suggBar) suggBar.style.display = 'none';

    // Show user's message immediately
    appendMessage('user', text);
    showTyping(true);

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });
        const data = await response.json();
        showTyping(false);

        if (data.reply) {
            appendMessage('bot', data.reply);
        } else {
            appendMessage('bot', '⚠️ Something went wrong. Please try again.');
        }
    } catch (err) {
        showTyping(false);
        appendMessage('bot', '⚠️ Network error. Make sure the server is running.');
    }

    // Re-enable input
    input.disabled = false;
    if (sendBtn) sendBtn.disabled = false;
    input.focus();
}

// Send a suggestion chip as a message
function sendSuggestion(text) {
    const input = document.getElementById('chatInput');
    if (input) {
        input.value = text;
        sendMessage();
    }
}

// Handle Enter / Shift+Enter in textarea
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// Clear chat history
async function clearChat() {
    if (!confirm('Clear all chat history?')) return;
    try {
        await fetch('/api/clear_chat', { method: 'POST' });
        const container = document.getElementById('chatMessages');
        if (container) container.innerHTML = '';
    } catch (err) {
        alert('Could not clear chat.');
    }
}

// Auto-resize textarea as user types
function setupAutoResize() {
    const input = document.getElementById('chatInput');
    if (!input) return;
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 150) + 'px';
    });
}

// ─────────────────────────────────────────────
// Radio Button Preference UI (dashboard)
// ─────────────────────────────────────────────
function setupRadioButtons() {
    document.querySelectorAll('.radio-option input[type="radio"]').forEach(radio => {
        radio.addEventListener('change', () => {
            // Remove active from siblings
            const group = radio.closest('.radio-group');
            if (group) group.querySelectorAll('.radio-option').forEach(opt => opt.classList.remove('active'));
            radio.closest('.radio-option').classList.add('active');
        });
    });
}

// ─────────────────────────────────────────────
// Progress Bar Animate on Load
// ─────────────────────────────────────────────
function animateProgressBar() {
    const fill = document.querySelector('.progress-fill');
    if (!fill) return;
    const target = fill.style.width;
    fill.style.width = '0%';
    setTimeout(() => { fill.style.width = target; }, 300);
}

// ─────────────────────────────────────────────
// Scroll to Bottom of Chat on Load
// ─────────────────────────────────────────────
function scrollChatToBottom() {
    const container = document.getElementById('chatMessages');
    if (container) container.scrollTop = container.scrollHeight;
}

// ─────────────────────────────────────────────
// Jinja2 doesn't have enumerate — add it via template filter
// (handled in app.py) but for quiz page we polyfill in JS
// ─────────────────────────────────────────────

// ─────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    renderAllMarkdown();
    setupAutoResize();
    setupRadioButtons();
    animateProgressBar();
    scrollChatToBottom();
});
