/**
 * Techvunex AI Website Assistant - Embeddable Chatbot Widget
 * Production-Ready Standalone Client
 * Zero-Flicker Progressive Streaming Architecture
 */
(function() {
  if (window.__TECHVUNEX_CHAT_INITIALIZED__) return;
  window.__TECHVUNEX_CHAT_INITIALIZED__ = true;

  const scriptTag = document.currentScript || (function() {
    const scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();

  const scriptSrc = scriptTag ? scriptTag.src : window.location.origin;
  const baseUrl = scriptSrc ? new URL(scriptSrc).origin : window.location.origin;

  // Load CSS stylesheet
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = `${baseUrl}/static/components/ChatWidget/chat.css`;
  document.head.appendChild(link);

  // State
  let isOpen = false;

  function generateNewSessionId() {
    return 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
  }

  // Purge any legacy stored messages so chats NEVER persist across visits or users
  try {
    localStorage.removeItem('techvunex_chat_messages');
    sessionStorage.removeItem('techvunex_chat_messages');
  } catch (e) {}

  let sessionId = generateNewSessionId();

  function saveStoredMessages(msgs) {
    // In-memory only: do not persist to localStorage so chats never leak across sessions/devices
  }

  const welcomeMessage = {
    id: 'msg_welcome',
    role: 'assistant',
    content: 'Hi 👋 I am the official AI Assistant for Techvunex Innovation. How can I assist you with custom software, website offers, CRM/ERP, or AI automation today?',
    sources: []
  };

  let messages = [welcomeMessage];

  const suggestedPrompts = [
    "100% Free Website Offer",
    "How much does a website cost?",
    "Pay 25% upfront & 12-month EMI",
    "100% Free SEO & SMO Support",
    "What services do you provide?",
    "I need a CRM solution"
  ];

  // DOM Elements
  let rootEl = null;
  let chatBoxEl = null;
  let messagesContainerEl = null;
  let typingIndicatorEl = null;
  let suggestionsBarEl = null;
  let inputFieldEl = null;
  let launcherBtnEl = null;
  let leadModalEl = null;

  function initDOM() {
    rootEl = document.createElement('div');
    rootEl.id = 'tv-chat-root';

    rootEl.innerHTML = `
      <!-- Launcher Button -->
      <button class="tv-launcher-btn" id="tv-toggle-btn" aria-label="Open Techvunex Assistant">
        <span id="tv-launcher-icon">💬</span>
        <span class="tv-launcher-badge"></span>
      </button>

      <!-- Chat Window -->
      <div class="tv-chat-window" id="tv-chat-box" style="display: none;">
        <!-- Header -->
        <div class="tv-chat-header">
          <div class="tv-header-info">
            <div class="tv-avatar">T</div>
            <div>
              <div class="tv-header-title">Techvunex AI</div>
              <div class="tv-header-status"><span class="tv-status-dot"></span> Online</div>
            </div>
          </div>
          <div class="tv-header-actions">
            <button class="tv-icon-btn" id="tv-btn-new-chat" title="New Chat (Fresh Session)">➕</button>
            <button class="tv-icon-btn" id="tv-btn-lead" title="Request Consultation">📋</button>
            <button class="tv-icon-btn" id="tv-btn-clear" title="Clear Conversation">🗑️</button>
            <button class="tv-icon-btn" id="tv-btn-close" title="Close">✕</button>
          </div>
        </div>

        <!-- Messages Area -->
        <div class="tv-messages-container" id="tv-messages">
          <!-- Dynamic messages are appended here -->
          <div class="tv-typing-indicator" id="tv-typing" style="display: none;">
            <span class="tv-dot"></span>
            <span class="tv-dot"></span>
            <span class="tv-dot"></span>
          </div>
        </div>

        <!-- Suggested Chips -->
        <div class="tv-suggestions-bar" id="tv-suggestions"></div>

        <!-- Input Bar -->
        <form class="tv-input-form" id="tv-form">
          <input type="text" id="tv-input" class="tv-input-field" placeholder="Ask about free website, pricing, services..." autocomplete="off" />
          <button type="submit" class="tv-send-btn" id="tv-send">➤</button>
        </form>

        <!-- Lead Modal -->
        <div class="tv-modal-backdrop" id="tv-lead-modal" style="display: none;">
          <div class="tv-lead-card">
            <div class="tv-lead-title">Connect with Techvunex Team</div>
            <div class="tv-lead-subtitle">Get a dedicated scope evaluation and custom quotation.</div>
            <form id="tv-lead-form" class="tv-lead-form">
              <input type="text" id="lead-name" placeholder="Your Full Name *" required />
              <input type="email" id="lead-email" placeholder="Business Email *" required />
              <input type="tel" id="lead-phone" placeholder="Phone Number *" required />
              <input type="text" id="lead-company" placeholder="Company Name" />
              <select id="lead-service">
                <option value="Website Development">Website Development</option>
                <option value="100% Free Website Offer">100% Free Website Offer</option>
                <option value="CRM & ERP Solutions">CRM & ERP Solutions</option>
                <option value="AI Automation & Chatbots">AI Automation & Chatbots</option>
                <option value="Mobile App Development">Mobile App Development</option>
                <option value="Custom Software Development">Custom Software Development</option>
                <option value="Cloud Solutions & DevOps">Cloud Solutions & DevOps</option>
                <option value="UI/UX Design">UI/UX Design</option>
                <option value="Digital Marketing & SEO">Digital Marketing & SEO</option>
              </select>
              <input type="text" id="lead-requirement" placeholder="Brief Project Requirement" />
              <div class="tv-modal-btns">
                <button type="submit" class="tv-btn-primary">Submit Request</button>
                <button type="button" class="tv-btn-cancel" id="tv-lead-cancel">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(rootEl);

    // Cache elements
    chatBoxEl = document.getElementById('tv-chat-box');
    messagesContainerEl = document.getElementById('tv-messages');
    typingIndicatorEl = document.getElementById('tv-typing');
    suggestionsBarEl = document.getElementById('tv-suggestions');
    inputFieldEl = document.getElementById('tv-input');
    launcherBtnEl = document.getElementById('tv-toggle-btn');
    leadModalEl = document.getElementById('tv-lead-modal');

    // Render suggestions
    renderSuggestions(suggestedPrompts);

    // Render initial messages
    messages.forEach(m => appendMessageToDOM(m));

    // Bind event listeners
    bindDOMEvents();
  }

  function renderSuggestions(prompts) {
    if (!suggestionsBarEl) return;
    suggestionsBarEl.innerHTML = prompts.map(p => {
      const safe = p.replace(/"/g, '&quot;');
      return `<button class="tv-suggestion-chip" data-prompt="${safe}">${p}</button>`;
    }).join('');

    suggestionsBarEl.querySelectorAll('.tv-suggestion-chip').forEach(btn => {
      btn.onclick = () => {
        const text = btn.getAttribute('data-prompt');
        if (text) sendMessage(text);
      };
    });
  }

  function appendMessageToDOM(msg) {
    const msgEl = document.createElement('div');
    msgEl.className = `tv-msg tv-msg-${msg.role}`;
    msgEl.id = `tv-msg-${msg.id}`;

    let actionsHtml = '';
    if (msg.role === 'assistant') {
      actionsHtml = `
        <div class="tv-msg-actions">
          <button class="tv-action-btn tv-copy-btn" title="Copy">📋 Copy</button>
          <button class="tv-action-btn tv-thumb-up" title="Helpful">👍</button>
          <button class="tv-action-btn tv-thumb-down" title="Not helpful">👎</button>
        </div>
      `;
    }

    msgEl.innerHTML = `
      <div class="tv-bubble">
        <div class="tv-bubble-content" id="tv-content-${msg.id}">${formatMarkdown(msg.content)}</div>
      </div>
      ${actionsHtml}
    `;

    // Insert before typing indicator
    if (typingIndicatorEl && typingIndicatorEl.parentNode === messagesContainerEl) {
      messagesContainerEl.insertBefore(msgEl, typingIndicatorEl);
    } else {
      messagesContainerEl.appendChild(msgEl);
    }

    // Attach actions
    const copyBtn = msgEl.querySelector('.tv-copy-btn');
    if (copyBtn) {
      copyBtn.onclick = () => {
        navigator.clipboard.writeText(msg.content);
        copyBtn.textContent = '✓ Copied';
        setTimeout(() => { copyBtn.textContent = '📋 Copy'; }, 2000);
      };
    }

    const upBtn = msgEl.querySelector('.tv-thumb-up');
    if (upBtn) {
      upBtn.onclick = () => submitFeedback(msg.id, 1, upBtn);
    }

    const downBtn = msgEl.querySelector('.tv-thumb-down');
    if (downBtn) {
      downBtn.onclick = () => submitFeedback(msg.id, -1, downBtn);
    }

    smartScrollToBottom();
    return msgEl;
  }

  function updateAssistantMessage(id, text) {
    const contentEl = document.getElementById(`tv-content-${id}`);
    if (contentEl) {
      contentEl.innerHTML = formatMarkdown(text);
      smartScrollToBottom();
    }
  }

  function showTyping() {
    if (typingIndicatorEl) {
      typingIndicatorEl.style.display = 'flex';
      smartScrollToBottom();
    }
  }

  function hideTyping() {
    if (typingIndicatorEl) {
      typingIndicatorEl.style.display = 'none';
    }
  }

  function smartScrollToBottom() {
    if (!messagesContainerEl) return;
    const isNearBottom = messagesContainerEl.scrollHeight - messagesContainerEl.scrollTop - messagesContainerEl.clientHeight < 140;
    if (isNearBottom) {
      messagesContainerEl.scrollTop = messagesContainerEl.scrollHeight;
    }
  }

  function formatMarkdown(text) {
    if (!text) return '';
    let escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Strip any escaped markdown slashes e.g. \### -> ###
    escaped = escaped.replace(/\\+(#{1,6})\s*/g, '$1 ');

    // Headings
    escaped = escaped.replace(/^####\s+(.*)$/gm, '<h6 class="tv-md-h">$1</h6>');
    escaped = escaped.replace(/^###\s+(.*)$/gm, '<h5 class="tv-md-h">$1</h5>');
    escaped = escaped.replace(/^##\s+(.*)$/gm, '<h4 class="tv-md-h">$1</h4>');
    escaped = escaped.replace(/^#\s+(.*)$/gm, '<h3 class="tv-md-h">$1</h3>');

    // Inline code
    escaped = escaped.replace(/`([^`]+)`/g, '<code class="tv-code">$1</code>');
    // Bold
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic
    escaped = escaped.replace(/(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
    // Links [text](url)
    escaped = escaped.replace(/\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="tv-link">$1</a>');

    // Lists
    escaped = escaped.replace(/^[•\-\*]\s+(.*)$/gm, '<li>$1</li>');
    escaped = escaped.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');
    escaped = escaped.replace(/<\/ul>\s*<ul>/g, '');

    // Paragraphs
    const paragraphs = escaped.split(/\n{2,}/).map(p => {
      p = p.trim();
      if (!p) return '';
      if (p.startsWith('<ul>') || p.startsWith('<li>') || p.startsWith('<h') || p.startsWith('<code')) return p;
      return `<p>${p.replace(/\n/g, '<br/>')}</p>`;
    });

    return paragraphs.join('');
  }

  async function sendMessage(text) {
    if (!text || !text.trim()) return;
    const trimmed = text.trim();

    // 1. User Message
    const userMsg = {
      id: 'msg_u_' + Date.now(),
      role: 'user',
      content: trimmed,
      sources: []
    };
    messages.push(userMsg);
    saveStoredMessages(messages);
    appendMessageToDOM(userMsg);

    // 2. Show typing indicator while waiting for the first token
    showTyping();

    // 3. Prepare Assistant Message container
    const assistantId = 'msg_a_' + Date.now();
    const assistantMsg = {
      id: assistantId,
      role: 'assistant',
      content: '',
      sources: []
    };
    messages.push(assistantMsg);

    let assistantElementAppended = false;
    let hasReceivedFirstToken = false;

    try {
      const response = await fetch(`${baseUrl}/api/v1/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: trimmed })
      });

      if (!response.ok) throw new Error('Network error');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (dataStr === '[DONE]') continue;
            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'token') {
                // On first token: hide typing indicator and append empty assistant bubble
                if (!hasReceivedFirstToken) {
                  hasReceivedFirstToken = true;
                  hideTyping();
                  appendMessageToDOM(assistantMsg);
                  assistantElementAppended = true;
                }

                assistantMsg.content += data.token;
                updateAssistantMessage(assistantId, assistantMsg.content);
              } else if (data.type === 'metadata') {
                if (data.sources) assistantMsg.sources = data.sources;
                if (data.suggested_actions && data.suggested_actions.length) {
                  renderSuggestions(data.suggested_actions);
                }
              }
            } catch (e) {}
          }
        }
        saveStoredMessages(messages);
      }
    } catch (err) {
      if (!assistantElementAppended) {
        hideTyping();
        appendMessageToDOM(assistantMsg);
      }
      assistantMsg.content = "Sorry, I encountered an issue connecting to the assistant. Please try again or reach out directly at info@techvunex.in.";
      updateAssistantMessage(assistantId, assistantMsg.content);
    } finally {
      hideTyping();
    }
  }

  async function submitFeedback(messageId, rating, btnEl) {
    try {
      btnEl.style.opacity = '0.5';
      await fetch(`${baseUrl}/api/v1/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: sessionId,
          rating: rating,
          comment: `Feedback for message ${messageId}`
        })
      });
      btnEl.textContent = rating > 0 ? '👍 Sent' : '👎 Sent';
    } catch (e) {
      btnEl.style.opacity = '1';
    }
  }

  function startNewChatSession(promptConfirmation = false) {
    if (promptConfirmation && !confirm('Start a new conversation? Current chat will be reset.')) {
      return;
    }
    sessionId = generateNewSessionId();
    try {
      localStorage.removeItem('techvunex_chat_messages');
      sessionStorage.removeItem('techvunex_chat_messages');
    } catch (e) {}
    messages = [
      {
        id: 'msg_welcome_' + Date.now(),
        role: 'assistant',
        content: 'Hi 👋 I am the official AI Assistant for Techvunex Innovation. How can I assist you with custom software, website offers, CRM/ERP, or AI automation today?',
        sources: []
      }
    ];
    if (messagesContainerEl) {
      messagesContainerEl.innerHTML = `
        <div class="tv-typing-indicator" id="tv-typing" style="display: none;">
          <span class="tv-dot"></span>
          <span class="tv-dot"></span>
          <span class="tv-dot"></span>
        </div>
      `;
      typingIndicatorEl = document.getElementById('tv-typing');
      appendMessageToDOM(messages[0]);
    }
    if (suggestionsBarEl) {
      renderSuggestions(suggestedPrompts);
    }
  }

  function openChat() {
    isOpen = true;
    if (chatBoxEl) chatBoxEl.style.display = 'flex';
    const icon = document.getElementById('tv-launcher-icon');
    if (icon) icon.textContent = '✕';
    if (inputFieldEl) {
      setTimeout(() => inputFieldEl.focus(), 100);
    }
  }

  function closeChat() {
    isOpen = false;
    if (chatBoxEl) chatBoxEl.style.display = 'none';
    const icon = document.getElementById('tv-launcher-icon');
    if (icon) icon.textContent = '💬';

    // Reset conversation immediately on close so old chats never linger
    startNewChatSession(false);
  }

  function toggleChat() {
    if (isOpen) {
      closeChat();
    } else {
      openChat();
    }
  }

  // Global API accessible from any button or script on host website
  window.TechvunexChat = {
    open: openChat,
    close: closeChat,
    toggle: toggleChat,
    reset: () => startNewChatSession(false),
    send: (message) => {
      openChat();
      if (message && typeof message === 'string') {
        sendMessage(message);
      }
    }
  };

  function bindDOMEvents() {
    // Launcher button toggle
    if (launcherBtnEl) {
      launcherBtnEl.onclick = toggleChat;
    }

    // Check if host website wants to hide default floating circular launcher
    const hideLauncher = scriptTag && (
      scriptTag.getAttribute('data-hide-launcher') === 'true' ||
      scriptTag.getAttribute('data-no-launcher') === 'true'
    );
    if (hideLauncher && launcherBtnEl) {
      launcherBtnEl.style.display = 'none';
    }

    // Delegate clicks for any button with data-techvunex-open, data-open-chat, or .open-techvunex-chat
    document.addEventListener('click', (e) => {
      const trigger = e.target && e.target.closest && e.target.closest('[data-techvunex-open], [data-open-chat], .open-techvunex-chat, .tv-open-chat');
      if (trigger) {
        e.preventDefault();
        openChat();
        const prompt = trigger.getAttribute('data-techvunex-prompt');
        if (prompt) {
          sendMessage(prompt);
        }
      }
    });

    // Close button inside header
    const closeBtn = document.getElementById('tv-btn-close');
    if (closeBtn) closeBtn.onclick = closeChat;

    const newChatBtn = document.getElementById('tv-btn-new-chat');
    if (newChatBtn) newChatBtn.onclick = () => startNewChatSession(true);

    const clearBtn = document.getElementById('tv-btn-clear');
    if (clearBtn) clearBtn.onclick = () => startNewChatSession(true);

    // Lead Modal
    const leadBtn = document.getElementById('tv-btn-lead');
    if (leadBtn) leadBtn.onclick = () => { leadModalEl.style.display = 'flex'; };

    const leadCancel = document.getElementById('tv-lead-cancel');
    if (leadCancel) leadCancel.onclick = () => { leadModalEl.style.display = 'none'; };

    const leadForm = document.getElementById('tv-lead-form');
    if (leadForm) leadForm.onsubmit = async (e) => {
      e.preventDefault();
      const payload = {
        name: document.getElementById('lead-name').value,
        email: document.getElementById('lead-email').value,
        phone: document.getElementById('lead-phone').value,
        company: document.getElementById('lead-company').value,
        service: document.getElementById('lead-service').value,
        requirement: document.getElementById('lead-requirement').value,
        source: 'chat_widget_modal'
      };

      try {
        await fetch(`${baseUrl}/api/v1/leads`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        leadModalEl.style.display = 'none';
        const confirmMsg = {
          id: 'msg_lead_confirm_' + Date.now(),
          role: 'assistant',
          content: `Thank you, **${payload.name}**! Your request for **${payload.service}** has been received. Our engineering and consulting team will reach out to you shortly via ${payload.email}.`,
          sources: []
        };
        messages.push(confirmMsg);
        appendMessageToDOM(confirmMsg);
      } catch (err) {
        alert('Could not submit request. Please reach out to info@techvunex.in');
      }
    };

    // Input form submit
    const form = document.getElementById('tv-form');
    if (form) form.onsubmit = (e) => {
      e.preventDefault();
      const val = inputFieldEl.value.trim();
      if (val) {
        sendMessage(val);
        inputFieldEl.value = '';
      }
    };
  }

  // Initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDOM);
  } else {
    initDOM();
  }
})();
