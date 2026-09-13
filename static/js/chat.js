/**
 * PRODUCTION-GRADE CHAT APPLICATION
 * Sender messages on RIGHT, Receiver messages on LEFT
 */

const ChatApp = {
  // ===== DOM REFERENCES =====
  dom: {},

  // ===== STATE MANAGEMENT =====
  state: {
    currentUserId: null,
    currentUserRole: null,
    currentConversationId: null,
    currentConversationType: null,
    pendingReceiverId: null,
    conversations: [],
    messages: {},
    isGroupChat: false,
    selectedDMRole: null,
    replyToMessage: null,
    searchTerm: '',
    onlineUsers: new Set(),
  },

  socket: null,

  // ===== UTILITIES =====
  util: {
    safeText: (str) => String(str || '').trim(),
    formatTime: (iso) => {
      if (!iso) return '';
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    },
    formatDate: (iso) => {
      if (!iso) return '';
      const d = new Date(iso);
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    },
    getInitials: (name) => {
      if (!name) return 'U';
      return name.trim().split(/\s+/).slice(0, 2).map(n => n[0]).join('').toUpperCase();
    },
    getUserColor: (userId) => {
      const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];
      let hash = 0;
      for (let i = 0; i < userId.length; i++) {
        hash = userId.charCodeAt(i) + ((hash << 5) - hash);
      }
      return colors[Math.abs(hash) % colors.length];
    },
  },

  // ===== INITIALIZATION =====
  init() {
    console.log('🚀 ChatApp Initializing');
    try {
      this.cacheDOM();
      this.state.currentUserId = this.dom.currentUserId;
      this.state.currentUserRole = this.dom.currentUserRole;
      this.setupSocket();
      this.setupEventListeners();
      this.setupMessageSearch();
      this.setupGroupSettings();
      this.loadConversations();
      console.log('✅ ChatApp Ready');
    } catch (err) {
      console.error('❌ Init failed:', err);
      this.showError('Failed to initialize chat');
    }
  },

  cacheDOM() {
    this.dom = {
      currentUserId: document.getElementById('current-user-id').value,
      currentUserRole: document.getElementById('current-user-role').value,
      conversationList: document.getElementById('conversationList'),
      newDMBtn: document.getElementById('newDMBtn'),
      newGroupBtn: document.getElementById('newGroupBtn'),
      refreshBtn: document.getElementById('refreshConvos'),
      convoSearch: document.getElementById('convoSearch'),
      dmComposerWrapper: document.getElementById('dmComposerWrapper'),
      dmCancelBtn: document.getElementById('dm_cancel'),
      rightTitle: document.getElementById('rightTitle'),
      rightSub: document.getElementById('rightSub'),
      rightAvatar: document.getElementById('rightAvatar'),
      messagesContainer: document.getElementById('messages'),
      messageInput: document.getElementById('messageInput'),
      sendBtn: document.getElementById('sendDirect'),
      backBtn: document.getElementById('backToConversations'),
      menuBtn: document.getElementById('menuBtn'),
      menuDropdown: document.getElementById('menuDropdown'),
      msgContextMenu: document.getElementById('msgContextMenu'),
      msgActionModal: document.getElementById('msgActionModal'),
      modalConfirm: document.getElementById('modalConfirm'),
      modalCancel: document.getElementById('modalCancel'),
      groupSettingsModal: document.getElementById('groupSettingsModal'),
      replyDiv: document.getElementById('replyDiv'),
    };
  },

  // ===== SOCKET.IO =====
  setupSocket() {
    this.socket = io();

    this.socket.on('connect', () => {
      console.log('✅ Socket connected');
      this.socket.emit('join', { user_id: this.state.currentUserId });
    });

    this.socket.on('new_message', (data) => {
      if (data.conversation_id === this.state.currentConversationId) {
        this.appendMessage(data.message);
      }
      this.loadConversations();
    });

    this.socket.on('presence_update', (data) => {
      if (data.status === 'online') {
        this.state.onlineUsers.add(data.user_public_id);
      } else {
        this.state.onlineUsers.delete(data.user_public_id);
      }
      this.updatePresenceIndicator();
    });

    this.socket.on('message_edited', (data) => {
      if (data.conversation_id === this.state.currentConversationId) {
        this.updateMessageInUI(data.message);
      }
    });

    this.socket.on('message_deleted', (data) => {
      if (data.conversation_id === this.state.currentConversationId) {
        this.removeMessageFromUI(data.message_id);
      }
    });

    this.socket.on('reaction_added', (data) => {
      this.addReactionToUI(data.message_id, data.reaction);
    });

    this.socket.on('reaction_removed', (data) => {
      this.removeReactionFromUI(data.message_id, data.user_public_id, data.emoji);
    });

    this.socket.on('disconnect', () => {
      console.warn('⚠️ Socket disconnected');
    });
  },

  // ===== EVENT LISTENERS =====
  setupEventListeners() {
    // Buttons
    this.dom.newDMBtn.addEventListener('click', () => this.openDMComposer());
    this.dom.newGroupBtn.addEventListener('click', () => this.openGroupCreator());
    this.dom.refreshBtn.addEventListener('click', () => this.loadConversations());
    this.dom.dmCancelBtn.addEventListener('click', () => this.closeDMComposer());

    // Messages
    this.dom.sendBtn.addEventListener('click', () => this.sendMessage());
    this.dom.messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // Auto-resize textarea
    this.dom.messageInput.addEventListener('input', () => {
      this.dom.messageInput.style.height = 'auto';
      this.dom.messageInput.style.height = Math.min(this.dom.messageInput.scrollHeight, 160) + 'px';
    });

    // Toggle send icon (microphone vs paper-plane) depending on message content
    try {
      const sendIcon = document.getElementById('sendIcon');
      const updateSendIcon = () => {
        const text = (this.dom.messageInput.value || '').trim();
        if (text.length > 0) {
          sendIcon.className = 'fas fa-paper-plane';
          this.dom.sendBtn.classList.add('has-text');
          this.dom.sendBtn.setAttribute('title', 'Send message');
        } else {
          sendIcon.className = 'fas fa-microphone';
          this.dom.sendBtn.classList.remove('has-text');
          this.dom.sendBtn.setAttribute('title', 'Record voice message');
        }
      };
      // run once and on input
      updateSendIcon();
      this.dom.messageInput.addEventListener('input', updateSendIcon);
    } catch (e) {
      console.warn('Send icon toggle not initialized:', e);
    }

    // Back button
    if (this.dom.backBtn) {
      this.dom.backBtn.addEventListener('click', () => this.closeConversation());
    }

    // Menu
    this.dom.menuBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      const visible = this.dom.menuDropdown.style.display === 'block';
      this.dom.menuDropdown.style.display = visible ? 'none' : 'block';
    });

    // Menu actions
    this.dom.menuDropdown?.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => {
        this.handleMenuAction(btn.dataset.action);
        this.dom.menuDropdown.style.display = 'none';
      });
    });

    // Search
    if (this.dom.convoSearch) {
      this.dom.convoSearch.addEventListener('input', (e) => {
        this.state.searchTerm = e.target.value.toLowerCase();
        this.renderConversationList();
      });
    }

    // DM roles
    document.querySelectorAll('.dm-role-btn').forEach(btn => {
      btn.addEventListener('click', () => this.selectDMRole(btn.dataset.role));
    });

    // Close menus on outside click
    document.addEventListener('click', () => {
      this.dom.menuDropdown.style.display = 'none';
      this.dom.msgContextMenu.style.display = 'none';
    });

    // Modal cancel
    this.dom.modalCancel?.addEventListener('click', () => {
      this.dom.msgActionModal.style.display = 'none';
    });

    // Message search close
    document.getElementById('closeMessageSearch')?.addEventListener('click', () => {
      document.getElementById('messageSearchBar').style.display = 'none';
      document.getElementById('messageSearchInput').value = '';
      this.filterMessages('');
    });

    // Group settings modal close
    document.getElementById('groupSettingsModal')?.addEventListener('click', (e) => {
      if (e.target.id === 'groupSettingsModal') {
        document.getElementById('groupSettingsModal').style.display = 'none';
      }
    });
  },

  // ===== CONVERSATIONS =====
  async loadConversations() {
    try {
      const res = await fetch('/chat/conversations');
      if (!res.ok) throw new Error('Failed to load');
      this.state.conversations = await res.json();
      this.renderConversationList();
      console.log('✅ Loaded', this.state.conversations.length, 'conversations');
    } catch (err) {
      console.error('❌ loadConversations:', err);
      this.showError('Failed to load conversations');
    }
  },

  renderConversationList() {
    const list = this.dom.conversationList;
    list.innerHTML = '';

    let convs = this.state.conversations;

    // Filter
    if (this.state.searchTerm) {
      convs = convs.filter(c => {
        const name = (c.name || '').toLowerCase();
        const preview = (c.last_message?.content || '').toLowerCase();
        return name.includes(this.state.searchTerm) || preview.includes(this.state.searchTerm);
      });
    }

    // Sort
    convs.sort((a, b) => {
      const au = a.unread_count || 0;
      const bu = b.unread_count || 0;
      if (au !== bu) return bu - au;
      return new Date(b.updated_at || 0) - new Date(a.updated_at || 0);
    });

    if (convs.length === 0) {
      list.innerHTML = '<div class="no-conversations">No conversations</div>';
      return;
    }

    convs.forEach(conv => {
      const item = document.createElement('div');
      item.className = 'conv-item' + (conv.id === this.state.currentConversationId ? ' active' : '');
      item.dataset.conversationId = conv.id;

      const other = conv.type === 'direct'
        ? conv.participants.find(p => p.user_public_id !== this.state.currentUserId) || conv.participants[0]
        : conv.participants[0];

      // Avatar
      const avatar = document.createElement('div');
      avatar.className = 'conv-avatar';
      avatar.style.background = this.util.getUserColor(other?.user_public_id || '');
      if (conv.type === 'group') {
        avatar.textContent = conv.participants?.length || '0';
        avatar.style.background = '#0ea5e9';
      } else {
        avatar.textContent = this.util.getInitials(other?.name);
      }
      item.appendChild(avatar);

      // Content
      const content = document.createElement('div');
      content.className = 'conv-content';

      const title = document.createElement('div');
      title.className = 'conv-title';
      title.textContent = (conv.type === 'group' ? '👥 ' : '') + (conv.name || other?.name || 'Chat');
      content.appendChild(title);

      const preview = document.createElement('div');
      preview.className = 'conv-preview';
      if (conv.last_message) {
        const text = conv.last_message.content || '';
        preview.textContent = text.slice(0, 50) + (text.length > 50 ? '...' : '');
      } else {
        preview.textContent = 'No messages';
        preview.style.color = '#999';
      }
      content.appendChild(preview);

      item.appendChild(content);

      // Unread badge
      if (conv.unread_count && conv.unread_count > 0) {
        const badge = document.createElement('span');
        badge.className = 'badge';
        badge.textContent = conv.unread_count;
        item.appendChild(badge);
      }

      item.addEventListener('click', () => this.openConversation(conv.id));
      
      // Mobile: Long-press touch support for conversation
      let touchStartTime = 0;
      let touchStartX = 0;
      let touchStartY = 0;
      const LONG_PRESS_DURATION = 500;

      item.addEventListener('touchstart', (e) => {
        touchStartTime = Date.now();
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
      }, false);

      item.addEventListener('touchend', (e) => {
        const duration = Date.now() - touchStartTime;
        const distX = Math.abs(e.changedTouches[0].clientX - touchStartX);
        const distY = Math.abs(e.changedTouches[0].clientY - touchStartY);
        const movedTooMuch = distX > 10 || distY > 10;

        if (duration > LONG_PRESS_DURATION && !movedTooMuch) {
          e.preventDefault();
          e.stopPropagation();
          // Show conversation context menu
          const menu = document.getElementById('convContextMenu');
          menu.style.display = 'block';
          menu.style.left = touchStartX + 'px';
          menu.style.top = touchStartY + 'px';
          window.currentContextConvo = item;
        }
        touchStartTime = 0;
      }, false);
      
      list.appendChild(item);
    });
  },

  async openConversation(convId) {
    try {
      this.state.currentConversationId = convId;
      this.state.pendingReceiverId = null;

      const conv = this.state.conversations.find(c => c.id === convId);
      if (!conv) throw new Error('Conversation not found');

      this.state.currentConversationType = conv.type;
      this.state.isGroupChat = conv.type === 'group';

      // Load messages
      const res = await fetch(`/chat/conversations/${convId}/messages`);
      if (!res.ok) throw new Error('Failed to load messages');
      const msgs = await res.json();
      this.state.messages[convId] = msgs;

      // Render
      this.renderMessages(msgs);
      
      // Update header with error handling
      try {
        this.updateConversationHeader(conv);
      } catch (headerErr) {
        console.warn('Header update error (non-critical):', headerErr);
      }
      
      this.markAsRead(convId);
      this.renderConversationList();
      this.dom.dmComposerWrapper.style.display = 'none';
      
      // Sync call inputs with error handling
      try {
        this.syncCallInputs(conv);
      } catch (syncErr) {
        console.warn('Call input sync error (non-critical):', syncErr);
      }

      console.log('✅ Opened conversation', convId);
    } catch (err) {
      console.error('❌ openConversation:', err);
      // Only show error if we actually failed to load
      if (err.message.includes('Failed to load') || err.message.includes('not found')) {
        this.showError('Failed to open conversation: ' + err.message);
      }
    }
  },

  closeConversation() {
    this.state.currentConversationId = null;
    this.dom.messagesContainer.innerHTML = '';
    this.dom.rightTitle.textContent = 'Select conversation';
    this.dom.rightSub.textContent = 'Open a chat to start';
  },

  updateConversationHeader(conv) {
    const other = conv.type === 'direct'
      ? conv.participants.find(p => p.user_public_id !== this.state.currentUserId) || conv.participants[0]
      : null;

    if (conv.type === 'group') {
      this.dom.rightTitle.textContent = '👥 ' + (conv.name || 'Group');
      // show group member metadata only for groups
      const memberCount = conv.participants?.length || 0;
      const meta = document.getElementById('groupMeta');
      const metaCount = document.getElementById('groupMemberCount');
      if (meta && metaCount) {
        meta.style.display = 'block';
        metaCount.textContent = `${memberCount} members`;
      }
      this.dom.rightSub.textContent = '';
      this.dom.rightAvatar.style.background = '#0ea5e9';
      this.dom.rightAvatar.textContent = String(memberCount || '0');
    } else {
      // hide group meta for direct messages
      const meta = document.getElementById('groupMeta');
      if (meta) meta.style.display = 'none';
      this.dom.rightTitle.textContent = other?.name || 'Unknown';
      const online = this.state.onlineUsers.has(other?.user_public_id);
      this.dom.rightSub.textContent = online ? '🟢 Online' : '⚫ Offline';
      this.dom.rightAvatar.textContent = this.util.getInitials(other?.name);
      this.dom.rightAvatar.style.background = this.util.getUserColor(other?.user_public_id || '');
    }
  },

  syncCallInputs(conv) {
    const idInput = document.getElementById('current-conversation-id');
    const typeInput = document.getElementById('current-conversation-type');
    const targetInput = document.getElementById('current-conversation-target');

    if (!idInput || !typeInput || !targetInput) return;

    idInput.value = conv.id;
    typeInput.value = conv.type === 'group' ? 'group' : 'direct';

    if (conv.type === 'direct') {
      const other = conv.participants.find(p => p.user_public_id !== this.state.currentUserId);
      targetInput.value = other?.user_public_id || '';
    }

    [idInput, typeInput, targetInput].forEach(input => {
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
  },

  // ===== MESSAGES =====
  renderMessages(messages) {
    const container = this.dom.messagesContainer;
    container.innerHTML = '';

    if (!messages || messages.length === 0) {
      container.innerHTML = '<div class="no-messages">No messages yet</div>';
      return;
    }

    // Group by day
    const byDay = {};
    messages.forEach(msg => {
      const key = new Date(msg.created_at).toDateString();
      if (!byDay[key]) byDay[key] = [];
      byDay[key].push(msg);
    });

    // Render
    Object.keys(byDay).sort().forEach(day => {
      const sep = document.createElement('div');
      sep.className = 'date-separator';
      sep.style.textAlign = 'center';
      sep.style.fontSize = '12px';
      sep.style.color = '#999';
      sep.style.margin = '15px 0';
      sep.textContent = this.util.formatDate(byDay[day][0].created_at);
      container.appendChild(sep);

      byDay[day].forEach(msg => {
        const el = this.createMessageElement(msg);
        container.appendChild(el);
      });
    });

    container.scrollTop = container.scrollHeight;
  },

  createMessageElement(msg) {
    const isMine = msg.sender_public_id === this.state.currentUserId;
    
    // Message wrapper - handles alignment
    const wrapper = document.createElement('div');
    wrapper.className = 'message-item';
    wrapper.style.display = 'flex';
    wrapper.style.justifyContent = isMine ? 'flex-end' : 'flex-start';
    wrapper.style.marginBottom = '10px';
    wrapper.style.paddingX = '10px';
    wrapper.dataset.messageId = msg.id;

    // Message bubble
    const bubble = document.createElement('div');
    bubble.style.maxWidth = '70%';
    bubble.style.wordWrap = 'break-word';
    bubble.style.padding = '10px 12px';
    bubble.style.borderRadius = '8px';
    bubble.style.background = isMine ? '#4CAF50' : '#f0f0f0';
    bubble.style.color = isMine ? 'white' : '#333';

    // Sender name (group only)
    if (!isMine && this.state.isGroupChat) {
      const name = document.createElement('div');
      name.textContent = msg.sender_name || 'Unknown';
      name.style.fontSize = '12px';
      name.style.fontWeight = '600';
      name.style.marginBottom = '4px';
      name.style.color = this.util.getUserColor(msg.sender_public_id);
      bubble.appendChild(name);
    }

    // Reply quote
    if (msg.reply_to) {
      const quote = document.createElement('div');
      quote.style.borderLeftColor = this.util.getUserColor(msg.reply_to.sender_public_id);
      quote.style.borderLeftWidth = '3px';
      quote.style.borderLeftStyle = 'solid';
      quote.style.paddingLeft = '8px';
      quote.style.marginBottom = '8px';
      quote.style.fontSize = '12px';
      quote.style.opacity = '0.8';
      quote.innerHTML = `
        <strong style="color: ${this.util.getUserColor(msg.reply_to.sender_public_id)};">
          ${msg.reply_to.sender_name}
        </strong>
        <div>${this.util.safeText(msg.reply_to.content).slice(0, 60)}</div>
      `;
      bubble.appendChild(quote);
    }

    // Content
    const content = document.createElement('div');
    content.textContent = this.util.safeText(msg.content);
    content.style.fontSize = '14px';
    content.style.marginTop = '4px';
    bubble.appendChild(content);

    // Time
    const time = document.createElement('div');
    time.style.fontSize = '11px';
    time.style.opacity = '0.7';
    time.style.marginTop = '4px';
    time.textContent = this.util.formatTime(msg.created_at) + (msg.edited_at ? ' (edited)' : '');
    bubble.appendChild(time);

    wrapper.appendChild(bubble);

    // Reactions
    if (msg.reactions && msg.reactions.length > 0) {
      const reactDiv = document.createElement('div');
      reactDiv.className = 'message-reactions';
      reactDiv.style.display = 'flex';
      reactDiv.style.gap = '4px';
      reactDiv.style.marginTop = '6px';
      reactDiv.style.flexWrap = 'wrap';
      this.renderReactions(reactDiv, msg.reactions);
      wrapper.appendChild(reactDiv);
    }

    // Desktop: Context menu on right-click
    wrapper.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      wrapper.style.backgroundColor = 'rgba(200, 200, 200, 0.1)';
      this.showMessageMenu(e, msg, wrapper);
    });

    // Mobile: Long-press touch support
    let touchStartTime = 0;
    let touchStartX = 0;
    let touchStartY = 0;
    const LONG_PRESS_DURATION = 500;

    wrapper.addEventListener('touchstart', (e) => {
      touchStartTime = Date.now();
      touchStartX = e.touches[0].clientX;
      touchStartY = e.touches[0].clientY;
    }, false);

    wrapper.addEventListener('touchend', (e) => {
      const duration = Date.now() - touchStartTime;
      const distX = Math.abs(e.changedTouches[0].clientX - touchStartX);
      const distY = Math.abs(e.changedTouches[0].clientY - touchStartY);
      const movedTooMuch = distX > 10 || distY > 10;

      if (duration > LONG_PRESS_DURATION && !movedTooMuch) {
        e.preventDefault();
        wrapper.style.backgroundColor = 'rgba(200, 200, 200, 0.1)';
        // Create synthetic event for showMessageMenu
        const evt = {
          pageX: touchStartX,
          clientX: touchStartX,
          pageY: touchStartY,
          clientY: touchStartY
        };
        
        // Haptic feedback
        if (navigator.vibrate) {
          navigator.vibrate(30);
        }
        
        this.showMessageMenu(evt, msg, wrapper);
      }
      touchStartTime = 0;
    }, false);

    return wrapper;
  },

  appendMessage(msg) {
    if (msg.conversation_id !== this.state.currentConversationId) return;
    const container = this.dom.messagesContainer;
    if (container.querySelector('.no-messages')) container.innerHTML = '';
    const el = this.createMessageElement(msg);
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
  },

  updateMessageInUI(msg) {
    const el = document.querySelector(`[data-message-id="${msg.id}"]`);
    if (el) el.replaceWith(this.createMessageElement(msg));
  },

  removeMessageFromUI(msgId) {
    const el = document.querySelector(`[data-message-id="${msgId}"]`);
    if (el) el.remove();
  },

  renderReactions(container, reactions) {
    container.innerHTML = '';
    const grouped = {};
    reactions.forEach(r => {
      if (!grouped[r.emoji]) grouped[r.emoji] = [];
      grouped[r.emoji].push(r);
    });

    Object.keys(grouped).forEach(emoji => {
      const btn = document.createElement('button');
      btn.className = 'reaction-btn';
      btn.style.background = '#fff';
      btn.style.border = '1px solid #ddd';
      btn.style.padding = '3px 6px';
      btn.style.borderRadius = '12px';
      btn.style.fontSize = '11px';
      btn.style.cursor = 'pointer';
      btn.style.transition = 'all 0.2s';
      const hasMine = grouped[emoji].some(r => r.user_public_id === this.state.currentUserId);
      if (hasMine) {
        btn.style.borderColor = '#4CAF50';
        btn.style.background = '#e8f5e9';
      }
      btn.textContent = emoji + ' ' + grouped[emoji].length;
      btn.addEventListener('click', () => {
        const msgId = container.closest('[data-message-id]').dataset.messageId;
        this.toggleReaction(msgId, emoji, hasMine);
      });
      container.appendChild(btn);
    });
  },

  addReactionToUI(msgId, reaction) {
    const el = document.querySelector(`[data-message-id="${msgId}"]`);
    if (!el) return;
    let div = el.querySelector('.message-reactions');
    if (!div) {
      div = document.createElement('div');
      div.className = 'message-reactions';
      div.style.display = 'flex';
      div.style.gap = '4px';
      div.style.marginTop = '6px';
      div.style.flexWrap = 'wrap';
      el.appendChild(div);
    }
    this.renderReactions(div, [reaction]);
  },

  removeReactionFromUI(msgId, userPubId, emoji) {
    const el = document.querySelector(`[data-message-id="${msgId}"]`);
    if (!el) return;
    const div = el.querySelector('.message-reactions');
    if (!div) return;
    const btns = Array.from(div.querySelectorAll('.reaction-btn'));
    btns.forEach(btn => {
      if (btn.textContent.startsWith(emoji)) {
        const count = parseInt(btn.textContent.split(' ')[1]) - 1;
        if (count <= 0) btn.remove();
        else btn.textContent = emoji + ' ' + count;
      }
    });
  },

  async toggleReaction(msgId, emoji, hasMine) {
    if (!this.state.currentConversationId) return;
    const csrf = document.querySelector('meta[name="csrf-token"]').content;
    const method = hasMine ? 'DELETE' : 'POST';

    try {
      const res = await fetch(
        `/chat/conversations/${this.state.currentConversationId}/messages/${msgId}/react`,
        {
          method,
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
          body: JSON.stringify({ emoji })
        }
      );
      if (!res.ok) throw new Error();
    } catch (err) {
      this.showError('Failed to toggle reaction');
    }
  },

  // ===== SENDING MESSAGES =====
  async sendMessage() {
    const text = this.dom.messageInput.value.trim();
    if (!text) return;

    const csrf = document.querySelector('meta[name="csrf-token"]').content;
    const replyId = this.state.replyToMessage?.id || null;

    try {
      if (this.state.currentConversationId) {
        // Send to conversation
        const res = await fetch(`/chat/conversations/${this.state.currentConversationId}/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
          body: JSON.stringify({ message: text, reply_to_message_id: replyId })
        });

        if (!res.ok) throw new Error();
        const data = await res.json();
        if (!data.success) throw new Error(data.error);

        this.dom.messageInput.value = '';
        this.state.replyToMessage = null;
        this.updateReplyUI();
      } else if (this.state.pendingReceiverId) {
        // Create new DM
        const res = await fetch('/chat/send_dm', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
          body: JSON.stringify({ message: text, receiver_public_id: this.state.pendingReceiverId, reply_to_message_id: replyId })
        });

        if (!res.ok) throw new Error();
        const data = await res.json();
        if (!data.success) throw new Error(data.error);

        this.dom.messageInput.value = '';
        this.state.replyToMessage = null;
        this.updateReplyUI();

        await this.loadConversations();
        this.openConversation(data.conversation_id);
      }
    } catch (err) {
      console.error('❌ sendMessage:', err);
      this.showError('Failed to send message');
    }
  },

  // ===== DM COMPOSER =====
  openDMComposer() {
    this.state.selectedDMRole = null;
    this.dom.dmComposerWrapper.style.display = 'flex';
    document.getElementById('dmStepRole').style.display = 'block';
    document.getElementById('dmStepProgramme').style.display = 'none';
    document.getElementById('dmStepLevel').style.display = 'none';
    document.getElementById('dmStepUsers').style.display = 'none';
  },

  closeDMComposer() {
    this.dom.dmComposerWrapper.style.display = 'none';
  },

  async selectDMRole(role) {
    this.state.selectedDMRole = role;

    if (role === 'teacher') {
      document.getElementById('dmStepRole').style.display = 'none';
      document.getElementById('dmStepUsers').style.display = 'block';
      await this.loadUsers('teacher');
    } else {
      document.getElementById('dmStepRole').style.display = 'none';
      document.getElementById('dmStepProgramme').style.display = 'block';
      await this.loadProgrammes();
    }
  },

  async loadProgrammes() {
    try {
      const res = await fetch('/chat/programmes');
      const programmes = await res.json();
      const select = document.getElementById('dmProgrammeSelect');
      select.innerHTML = '<option value="">Choose programme</option>';
      programmes.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.name;
        opt.textContent = p.name;
        select.appendChild(opt);
      });

      select.onchange = async () => {
        if (select.value) {
          document.getElementById('dmStepProgramme').style.display = 'none';
          document.getElementById('dmStepLevel').style.display = 'block';
          await this.loadLevels();
        }
      };
    } catch (err) {
      this.showError('Failed to load programmes');
    }
  },

  async loadLevels() {
    try {
      const res = await fetch('/chat/levels');
      const levels = await res.json();
      const select = document.getElementById('dmLevelSelect');
      select.innerHTML = '<option value="">Choose level</option>';
      levels.forEach(l => {
        const opt = document.createElement('option');
        opt.value = l.level;
        opt.textContent = 'Level ' + l.level;
        select.appendChild(opt);
      });

      select.onchange = async () => {
        if (select.value) {
          document.getElementById('dmStepLevel').style.display = 'none';
          document.getElementById('dmStepUsers').style.display = 'block';
          const prog = document.getElementById('dmProgrammeSelect').value;
          await this.loadUsers('student', prog, select.value);
        }
      };
    } catch (err) {
      this.showError('Failed to load levels');
    }
  },

  async loadUsers(role, programme = null, level = null) {
    try {
      let url = `/chat/users?role=${role}`;
      if (programme) url += `&programme=${encodeURIComponent(programme)}`;
      if (level) url += `&level=${encodeURIComponent(level)}`;

      const res = await fetch(url);
      const users = await res.json();
      const list = document.getElementById('dmUserList');

      if (!users || users.length === 0) {
        list.innerHTML = '<p style="padding: 10px;">No users found</p>';
        return;
      }

      list.innerHTML = users.map(u => `
        <div class="user-item" data-user-id="${u.id}">
          <div class="user-avatar" style="background: ${this.util.getUserColor(u.id)}; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: 600;">${this.util.getInitials(u.name)}</div>
          <div style="flex: 1;">${u.name}</div>
        </div>
      `).join('');

      // Add styles to user items
      const style = document.createElement('style');
      style.textContent = `
        .user-item {
          display: flex;
          gap: 10px;
          padding: 8px 10px;
          cursor: pointer;
          border-bottom: 1px solid #eee;
          align-items: center;
          transition: background-color 0.2s;
        }
        .user-item:hover {
          background-color: #f5f5f5;
        }
      `;
      document.head.appendChild(style);

      list.querySelectorAll('.user-item').forEach(item => {
        item.onclick = async () => {
          await this.startDM(item.dataset.userId);
        };
      });
    } catch (err) {
      this.showError('Failed to load users');
    }
  },

  async startDM(userId) {
    const existing = this.state.conversations.find(c =>
      c.type === 'direct' && c.participants.some(p => p.user_public_id === userId)
    );

    if (existing) {
      this.closeDMComposer();
      this.openConversation(existing.id);
      return;
    }

    this.state.pendingReceiverId = userId;
    this.state.currentConversationId = null;
    this.closeDMComposer();
    this.dom.messagesContainer.innerHTML = '';
    this.dom.rightTitle.textContent = 'New Message';
    this.dom.rightSub.textContent = 'Start typing...';
  },

  // ===== GROUPS =====
  openGroupCreator() {
    const modal = document.getElementById('msgActionModal');
    const title = document.getElementById('modalTitle');
    const input = document.getElementById('modalInput');
    const convoList = document.getElementById('modalConvoList');
    const confirm = document.getElementById('modalConfirm');
    const confirmText = document.getElementById('modalConfirmText');

    title.textContent = 'Create New Group';
    // hide delete confirmation text (only for delete operations)
    confirmText.style.display = 'none';
    // show name input
    input.style.display = 'block';
    input.placeholder = 'Group name';
    input.value = '';

    // build programme/level selectors + members container
    convoList.innerHTML = `
      <div style="display:flex; gap:8px; margin-bottom:8px;">
        <select id="groupProgramme" style="flex:1; padding:8px; border-radius:6px; border:1px solid #e5e7eb;"></select>
        <select id="groupLevel" style="width:120px; padding:8px; border-radius:6px; border:1px solid #e5e7eb;"></select>
      </div>
      <div id="groupMembersList" style="max-height:220px; overflow:auto; border:1px solid #eee; padding:8px; border-radius:6px;"></div>
    `;

    // show modal
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    requestAnimationFrame(() => modal.classList.add('show'));

    confirm.textContent = 'Create Group';

    // load programmes and levels
    const loadProgrammes = async () => {
      try {
        const res = await fetch('/chat/programmes');
        const data = await res.json();
        const progSel = document.getElementById('groupProgramme');
        const lvlSel = document.getElementById('groupLevel');
        progSel.innerHTML = '<option value="">Select programme</option>' + (data.programmes || []).map(p => `<option value="${p}">${p}</option>`).join('');
        lvlSel.innerHTML = '<option value="">Level</option>' + (data.levels || []).map(l => `<option value="${l}">${l}</option>`).join('');
      } catch (err) {
        console.warn('Failed to load programmes', err);
      }
    };

    // keep selected members persistent across programme/level changes
    const selectedMembers = new Set();
    const memberNameMap = new Map(); // public_id -> display name

    const loadStudents = async () => {
      const prog = document.getElementById('groupProgramme').value;
      const lvl = document.getElementById('groupLevel').value;
      const list = document.getElementById('groupMembersList');
      list.innerHTML = '<div style="text-align:center; color:#999; padding:20px;">Loading...</div>';
      if (!prog || !lvl) { list.innerHTML = '<div style="text-align:center; color:#999; padding:20px;">Select programme and level to list students</div>'; return; }
      try {
        const res = await fetch(`/chat/students_by_programme?programme=${encodeURIComponent(prog)}&level=${encodeURIComponent(lvl)}`);
        const data = await res.json();
        if (!data.students || !data.students.length) { list.innerHTML = '<div style="text-align:center; color:#999; padding:20px;">No students found</div>'; return; }
        list.innerHTML = data.students.map(s => {
          // record name for later rendering in selected list
          memberNameMap.set(s.public_id, s.name);
          return `
          <label data-pubid="${s.public_id}" style="display:flex; align-items:center; gap:12px; padding:10px 12px; margin-bottom:4px; border-radius:8px; cursor:pointer; transition:all 0.2s ease; background:#f9f9f9;">
            <input type="checkbox" class="group-member-checkbox" value="${s.public_id}" style="width:18px; height:18px; cursor:pointer; flex-shrink:0;" ${selectedMembers.has(s.public_id) ? 'checked' : ''}>
            <div style="flex:1; font-size:14px; font-weight:500; color:#333;">${s.name}</div>
          </label>
        `;
        }).join('');
        // Add hover effect and checkbox handlers
        Array.from(list.querySelectorAll('label')).forEach(label => {
          label.addEventListener('mouseenter', () => { label.style.backgroundColor = '#f0f0f0'; label.style.transform = 'translateX(4px)'; });
          label.addEventListener('mouseleave', () => { label.style.backgroundColor = '#f9f9f9'; label.style.transform = 'translateX(0)'; });
          const cb = label.querySelector('input.group-member-checkbox');
          if (cb) {
            cb.addEventListener('change', () => {
              const id = cb.value;
              if (cb.checked) selectedMembers.add(id); else selectedMembers.delete(id);
            });
          }
        });
        // if there is a view selected button, enable it
        const viewBtn = document.getElementById('viewSelectedBtn');
        if (viewBtn) {
          viewBtn.onclick = () => {
            const container = document.getElementById('selectedMembersContainer');
            container.innerHTML = '';
            if (!selectedMembers.size) {
              container.innerHTML = '<div style="color:#666; padding:12px;">No members selected</div>';
            } else {
              Array.from(selectedMembers).forEach(id => {
                const name = memberNameMap.get(id) || id;
                const node = document.createElement('div');
                node.style.display = 'flex';
                node.style.justifyContent = 'space-between';
                node.style.alignItems = 'center';
                node.style.padding = '8px';
                node.style.borderBottom = '1px solid #f0f0f0';
                node.innerHTML = `<div style="font-weight:500; color:#222;">${name}</div><div style="color:#999; font-size:12px;">${id}</div>`;
                container.appendChild(node);
              });
            }
            document.getElementById('selectedMembersModal').style.display = 'block';
          };
        }
      } catch (err) {
        console.error('Failed to load students', err);
        list.innerHTML = '<div style="text-align:center; color:#999; padding:20px;">Failed to load students</div>';
      }
    };

    // wire selectors
    setTimeout(() => {
      loadProgrammes().then(() => {
        document.getElementById('groupProgramme').addEventListener('change', loadStudents);
        document.getElementById('groupLevel').addEventListener('change', loadStudents);
      });
    }, 0);

    // add a small 'View selected' control next to selectors
    const viewBtnWrap = document.createElement('div');
    viewBtnWrap.style.marginTop = '8px';
    viewBtnWrap.innerHTML = '<button id="viewSelectedBtn" class="btn btn-sm" style="padding:6px 10px;">View selected</button>';
    document.getElementById('groupMembersList').parentNode.insertBefore(viewBtnWrap, document.getElementById('groupMembersList'));

    // close handler for side modal
    const selectedModal = document.getElementById('selectedMembersModal');
    const selectedBackdrop = document.getElementById('selectedMembersBackdrop');
    const closeSelected = document.getElementById('closeSelectedModal');
    if (selectedBackdrop) selectedBackdrop.addEventListener('click', () => { selectedModal.style.display = 'none'; });
    if (closeSelected) closeSelected.addEventListener('click', () => { selectedModal.style.display = 'none'; });

    // replace confirm handler
    const newConfirm = confirm.cloneNode(true);
    confirm.parentNode.replaceChild(newConfirm, confirm);
    newConfirm.addEventListener('click', async () => {
      const name = input.value.trim();
      if (!name) return this.showError('Please provide a group name');
      const checked = Array.from(selectedMembers);
      if (!checked.length) return this.showError('Please select at least one member');
      try {
        const csrf = document.querySelector('meta[name="csrf-token"]').content;
        const res = await fetch('/chat/conversations/create_group', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
          body: JSON.stringify({ name, members: checked })
        });
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();
        this.showSuccess('Group created');
        modal.classList.remove('show');
        setTimeout(() => { modal.style.display = 'none'; document.body.style.overflow = 'auto'; }, 250);
        if (data && data.id) this.openConversation(data.id); else this.loadConversations();
      } catch (err) {
        console.error(err);
        this.showError('Failed to create group');
      }
    });
  },

  // ===== MENU =====
  handleMenuAction(action) {
    if (action === 'search') {
      this.dom.convoSearch?.focus();
    } else if (action === 'add_members') {
      if (this.state.isGroupChat) {
        this.showAddMembersDialog();
      } else {
        this.showError('Can only add members to groups');
      }
    } else if (action === 'mute') {
      this.toggleMuteConversation();
    } else if (action === 'clear_chat') {
      if (confirm('Clear chat history? This cannot be undone.')) {
        this.dom.messagesContainer.innerHTML = '';
        this.showSuccess('Chat cleared');
      }
    } else if (action === 'search_messages') {
      const searchBar = document.getElementById('messageSearchBar');
      if (searchBar) {
        searchBar.style.display = 'block';
        document.getElementById('messageSearchInput')?.focus();
      }
    }
  },

  async toggleMuteConversation() {
    if (!this.state.currentConversationId) return;
    
    const btn = document.querySelector('[data-action="mute"]');
    if (!btn) return;
    
    const isMuted = btn.innerHTML.includes('Unmute');
    const endpoint = isMuted ? 'unmute' : 'mute';
    
    try {
      const csrf = document.querySelector('meta[name="csrf-token"]').content;
      const res = await fetch(`/chat/${endpoint}/${this.state.currentConversationId}`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrf }
      });
      
      if (res.ok) {
        if (isMuted) {
          btn.innerHTML = '<i class="fas fa-bell-slash"></i> Mute';
        } else {
          btn.innerHTML = '<i class="fas fa-bell"></i> Unmute';
        }
        this.showSuccess(isMuted ? 'Unmuted' : 'Muted');
      }
    } catch (err) {
      this.showError('Failed to toggle mute');
    }
  },

  async showAddMembersDialog() {
    if (!this.state.isGroupChat) return;
    
    const modal = document.getElementById('msgActionModal');
    const title = document.getElementById('modalTitle');
    const input = document.getElementById('modalInput');
    const confirm = document.getElementById('modalConfirm');
    
    title.textContent = 'Add Members';
    input.placeholder = 'Enter member IDs (comma separated)';
    input.value = '';
    document.getElementById('modalConfirmText').style.display = 'none';
    modal.style.display = 'block';
    
    confirm.onclick = async () => {
      const memberIds = input.value.split(',').map(id => id.trim()).filter(id => id);
      if (!memberIds.length) {
        this.showError('No members specified');
        return;
      }
      
      try {
        const csrf = document.querySelector('meta[name="csrf-token"]').content;
        const res = await fetch(`/chat/conversations/${this.state.currentConversationId}/add_members`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
          body: JSON.stringify({ members: memberIds })
        });
        
        if (res.ok) {
          this.showSuccess('Members added');
          modal.style.display = 'none';
          this.loadConversations();
        }
      } catch (err) {
        this.showError('Failed to add members');
      }
    };
  },

  // ===== MESSAGE MENU =====
  showMessageMenu(e, msg, wrapper) {
    const menu = this.dom.msgContextMenu;
    
    // Store reference for cleanup
    if (!window.currentMessageWrapper) {
      window.currentMessageWrapper = null;
    }
    window.currentMessageWrapper = wrapper;
    
    // Set initial position
    menu.style.left = e.pageX + 'px';
    menu.style.top = e.pageY + 'px';
    menu.style.display = 'block';

    // Smart positioning - keep menu in viewport
    requestAnimationFrame(() => {
      const rect = menu.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      
      // Adjust horizontal position
      if (rect.right > viewportWidth - 10) {
        const newLeft = Math.max(10, viewportWidth - rect.width - 10);
        menu.style.left = newLeft + 'px';
      }
      
      // Adjust vertical position - prefer above, fallback below
      if (rect.bottom > viewportHeight - 10) {
        const newTop = Math.max(10, e.pageY - rect.height - 10);
        menu.style.top = newTop + 'px';
      }
    });

    const isMine = msg.sender_public_id === this.state.currentUserId;
    menu.querySelector('[data-action="edit"]').style.display = isMine ? 'block' : 'none';
    menu.querySelector('[data-action="delete"]').style.display = isMine ? 'block' : 'none';

    menu.querySelectorAll('button').forEach(btn => {
      btn.onclick = () => this.handleMessageAction(btn.dataset.action, msg);
    });
  },

  async handleMessageAction(action, msg) {
    const isMine = msg.sender_public_id === this.state.currentUserId;
    let shouldClose = true;

    if (action === 'reply') {
      this.state.replyToMessage = msg;
      this.updateReplyUI();
      this.dom.messageInput.focus();
    } else if (action === 'edit') {
      if (!isMine) return this.showError('Can only edit your own messages');
      const newText = prompt('Edit:', msg.content);
      if (newText && newText.trim()) {
        const csrf = document.querySelector('meta[name="csrf-token"]').content;
        try {
          await fetch(`/chat/conversations/${this.state.currentConversationId}/messages/${msg.id}/edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
            body: JSON.stringify({ content: newText.trim() })
          });
          this.showSuccess('Message updated');
          this.loadMessages();
        } catch {
          this.showError('Failed to edit');
        }
      }
    } else if (action === 'copy') {
      navigator.clipboard.writeText(msg.content);
      this.showSuccess('Copied to clipboard');
    } else if (action === 'forward') {
      this.showForwardDialog(msg);
      shouldClose = false; // Don't close yet, let forward dialog handle it
    } else if (action === 'delete') {
      if (!isMine) return this.showError('Can only delete your own messages');
      if (confirm('Delete message?')) {
        const csrf = document.querySelector('meta[name="csrf-token"]').content;
        try {
          await fetch(`/chat/conversations/${this.state.currentConversationId}/messages/${msg.id}/delete`, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrf }
          });
          this.showSuccess('Message deleted');
          this.loadMessages();
        } catch {
          this.showError('Failed to delete');
        }
      }
    } else if (action === 'react') {
      this.showReactionPicker(msg);
      shouldClose = false; // Don't close, let reaction picker stay visible
    }

    // Close menu with animation
    if (shouldClose) {
      const menu = this.dom.msgContextMenu;
      menu.classList.add('slide-out');
      setTimeout(() => {
        menu.style.display = 'none';
        menu.classList.remove('slide-out');
        // Clear background highlight
        if (window.currentMessageWrapper) {
          window.currentMessageWrapper.style.backgroundColor = '';
          window.currentMessageWrapper = null;
        }
      }, 200);
    }
  },

  async showForwardDialog(msg) {
    console.log('📤 Forward dialog opening', {msg});
    const modal = document.getElementById('msgActionModal');
    const title = document.getElementById('modalTitle');
    const convoList = document.getElementById('modalConvoList');
    const confirm = document.getElementById('modalConfirm');
    
    if (!modal) console.error('❌ Modal not found');
    if (!confirm) console.error('❌ Confirm button not found');
    
    title.textContent = '📤 Forward Message';
    
    // Show message preview
    const previewHTML = `
      <div style="background: #f5f5f5; padding: 10px; border-radius: 6px; margin-bottom: 15px; border-left: 3px solid #007bff;">
        <strong style="display: block; font-size: 0.9em; color: #666; margin-bottom: 5px;">Message to forward:</strong>
        <p style="margin: 0; padding: 8px; background: white; border-radius: 4px; word-break: break-word;">${this.escapeHtml(msg.content)}</p>
      </div>
    `;
    
    // Build conversation list with better styling
    const filteredConvos = this.state.conversations.filter(c => c.id !== this.state.currentConversationId);
    console.log(`📋 ${filteredConvos.length} conversations available to forward to`);
    
    let convoHTML = previewHTML;
    if (filteredConvos.length === 0) {
      convoHTML += '<p style="padding: 15px; text-align: center; color: #999; background: #f9f9f9; border-radius: 6px;">No other conversations available</p>';
    } else {
      convoHTML += `
        <div style="margin-bottom: 10px;">
          <strong style="display: block; margin-bottom: 8px; color: #333;">Select conversation to forward to:</strong>
          <div style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; border-radius: 6px;">
            ${filteredConvos.map((c, idx) => {
              const other = c.participants.find(p => p.user_public_id !== this.state.currentUserId) || c.participants[0];
              const displayName = c.name || other?.name || 'Chat';
              const lastMsg = c.last_message ? `${c.last_message.sender_name}: ${c.last_message.content.substring(0, 40)}${c.last_message.content.length > 40 ? '...' : ''}` : 'No messages yet';
              const isGroup = c.type === 'group';
              
              return `
                <label style="display: flex; align-items: center; padding: 12px; cursor: pointer; border-bottom: 1px solid #eee; transition: all 0.2s; background: white;" 
                       onmouseover="this.style.backgroundColor='#f9f9f9'" 
                       onmouseout="this.style.backgroundColor='white'">
                  <input type="radio" name="forward_convo" value="${c.id}" style="margin-right: 12px; cursor: pointer; width: 18px; height: 18px;">
                  <div style="flex: 1; min-width: 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                      <strong style="color: #333;">${this.escapeHtml(displayName)}</strong>
                      ${isGroup ? `<span style="font-size: 0.8em; color: #999; background: #f0f0f0; padding: 2px 6px; border-radius: 3px; margin-left: 6px;">${c.participants?.length || 0} members</span>` : ''}
                    </div>
                    <p style="margin: 0; font-size: 0.85em; color: #999; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(lastMsg)}</p>
                  </div>
                </label>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }
    
    convoList.innerHTML = convoHTML;
    
    document.getElementById('modalInput').style.display = 'none';
    document.getElementById('modalConfirmText').style.display = 'none';
    
    // Ensure modal is visible
    modal.style.display = 'flex';
    modal.style.visibility = 'visible';
    modal.style.opacity = '1';
    
    // Force a reflow to ensure CSS transitions work
    void modal.offsetHeight;
    
    // Add show class for animations
    modal.classList.add('show');
    console.log('✅ Modal opened with forward dialog');
    
    confirm.textContent = 'Forward Message';
    
    // Clone to remove old listeners
    const newConfirmBtn = confirm.cloneNode(true);
    confirm.parentNode.replaceChild(newConfirmBtn, confirm);
    const confirmBtn = document.getElementById('modalConfirm');
    
    // Add event listener
    const forwardHandler = async (e) => {
      console.log('🔔 Forward button clicked');
      e.preventDefault();
      e.stopPropagation();
      
      const targetConvoId = document.querySelector('input[name="forward_convo"]:checked')?.value;
      console.log('Target:', targetConvoId);
      
      if (!targetConvoId) {
        this.showError('Select a conversation');
        return;
      }
      
      try {
        const csrf = document.querySelector('meta[name="csrf-token"]').content;
        const messageBody = {
          message: `[Forwarded] ${msg.content}`,
          reply_to_message_id: null
        };
        console.log('📤 Sending:', messageBody);
        
        const res = await fetch(`/chat/conversations/${targetConvoId}/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
          body: JSON.stringify(messageBody)
        });
        
        console.log('Response:', res.status);
        const data = await res.json();
        console.log('Response data:', data);
        
        if (data.success) {
          this.showSuccess('Message forwarded!');
          modal.classList.remove('show');
          setTimeout(() => {
            modal.style.display = 'none';
          }, 300);
          this.loadConversations();
        } else {
          this.showError(data.error || 'Forward failed');
        }
      } catch (err) {
        console.error('Forward error:', err);
        this.showError('Error: ' + err.message);
      }
    };
    
    confirmBtn.addEventListener('click', forwardHandler);
    console.log('✅ Forward handler attached');
  },

  async showReactionPicker(msg) {
    const reactions = ['👍', '❤️', '😂', '😮', '😢', '🔥', '👏', '🙏'];
    const modal = document.getElementById('msgActionModal');
    const title = document.getElementById('modalTitle');
    const confirm = document.getElementById('modalConfirm');
    const convoList = document.getElementById('modalConvoList');
    
    title.textContent = 'Add Reaction';
    document.getElementById('modalInput').style.display = 'none';
    document.getElementById('modalConfirmText').style.display = 'none';
    
    convoList.innerHTML = reactions
      .map(emoji => `<button style="padding: 10px 15px; margin: 4px; font-size: 20px; border: 1px solid #ddd; border-radius: 4px; cursor: pointer; background: white;" data-emoji="${emoji}">${emoji}</button>`)
      .join('');
    
    modal.style.display = 'block';
    confirm.style.display = 'none';
    
    convoList.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', async () => {
        const emoji = btn.dataset.emoji;
        try {
          const csrf = document.querySelector('meta[name="csrf-token"]').content;
          const res = await fetch(`/chat/conversations/${this.state.currentConversationId}/messages/${msg.id}/react`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
            body: JSON.stringify({ emoji })
          });
          
          if (res.ok) {
            modal.style.display = 'none';
            confirm.style.display = 'block';
            this.loadMessages();
          }
        } catch (err) {
          this.showError('Failed to add reaction');
        }
      });
    });
  },

  // ===== REPLY =====
  updateReplyUI() {
    if (!this.dom.replyDiv) return;

    if (this.state.replyToMessage) {
      const msg = this.state.replyToMessage;
      this.dom.replyDiv.innerHTML = `
        <div style="border-left: 3px solid ${this.util.getUserColor(msg.sender_public_id)}; padding-left: 8px; flex: 1;">
          <strong style="color: ${this.util.getUserColor(msg.sender_public_id)};">${msg.sender_name}</strong>
          <div style="font-size: 12px;">${this.util.safeText(msg.content).slice(0, 60)}</div>
        </div>
        <button id="clearReply" style="background: none; border: none; cursor: pointer; font-size: 20px;">×</button>
      `;
      this.dom.replyDiv.style.display = 'flex';
      this.dom.replyDiv.style.alignItems = 'center';
      this.dom.replyDiv.style.gap = '8px';
      document.getElementById('clearReply').onclick = () => {
        this.state.replyToMessage = null;
        this.updateReplyUI();
      };
    } else {
      this.dom.replyDiv.style.display = 'none';
    }
  },

  // ===== UTILITY METHODS =====
  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },

  // ===== PRESENCE =====
  updatePresenceIndicator() {
    if (!this.state.currentConversationId) return;
    const conv = this.state.conversations.find(c => c.id === this.state.currentConversationId);
    if (!conv || conv.type === 'group') return;

    const other = conv.participants.find(p => p.user_public_id !== this.state.currentUserId);
    if (!other) return;

    const online = this.state.onlineUsers.has(other.user_public_id);
    this.dom.rightSub.textContent = online ? '🟢 Online' : '⚫ Offline';
  },

  // ===== UTILITIES =====
  async markAsRead(convId) {
    const csrf = document.querySelector('meta[name="csrf-token"]').content;
    try {
      await fetch('/chat/mark_read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ conversation_id: convId })
      });
    } catch (err) {
      console.warn('mark_read failed:', err);
    }
  },

  // ===== MESSAGE SEARCH =====
  setupMessageSearch() {
    const searchInput = document.getElementById('messageSearchInput');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase();
      this.filterMessages(query);
    });
  },

  filterMessages(query) {
    const messages = document.querySelectorAll('.msg-item, .msg-own');
    let foundCount = 0;

    messages.forEach(msg => {
      const content = msg.textContent.toLowerCase();
      if (query && content.includes(query)) {
        msg.style.display = 'block';
        msg.style.backgroundColor = '#fff3cd';
        foundCount++;
      } else if (query) {
        msg.style.display = 'none';
      } else {
        msg.style.display = 'block';
        msg.style.backgroundColor = 'transparent';
      }
    });

    if (query && foundCount === 0) {
      this.showError(`No messages found for "${query}"`);
    } else if (query) {
      this.showSuccess(`Found ${foundCount} message(s)`);
    }
  },

  // ===== GROUP SETTINGS =====
  setupGroupSettings() {
    const groupSettingsBtn = document.getElementById('groupSettingsBtn');
    if (!groupSettingsBtn) return;
    
    groupSettingsBtn.addEventListener('click', () => {
      if (!this.state.isGroupChat) {
        this.showError('Not a group chat');
        return;
      }
      this.showGroupSettingsModal();
    });
  },

  showGroupSettingsModal() {
    const modal = document.getElementById('groupSettingsModal');
    const conv = this.state.conversations.find(c => c.id === this.state.currentConversationId);
    
    if (!conv) return;
    
    const nameInput = document.getElementById('groupNameInput');
    const memberList = document.getElementById('groupMemberList');
    
    nameInput.value = conv.name || '';
    
    memberList.innerHTML = conv.participants.map(p => `
      <div style="padding: 8px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
        <span>${p.name}</span>
        <button style="padding: 4px 8px; background: #ff6b6b; color: white; border: none; border-radius: 4px; cursor: pointer;" data-user-id="${p.user_public_id}">Remove</button>
      </div>
    `).join('');
    
    // Remove member handlers
    memberList.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', async () => {
        const userId = btn.dataset.userId;
        if (confirm('Remove this member?')) {
          await this.removeMember(userId);
        }
      });
    });
    
    modal.style.display = 'block';
  },

  async removeMember(userId) {
    try {
      const csrf = document.querySelector('meta[name="csrf-token"]').content;
      const res = await fetch(`/chat/groups/${this.state.currentConversationId}/remove_member`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ member_public_id: userId })
      });
      
      if (res.ok) {
        this.showSuccess('Member removed');
        this.loadConversations();
      }
    } catch (err) {
      this.showError('Failed to remove member');
    }
  },

  showError(msg) {
    console.error('❌', msg);
    alert(msg);
  },

  showSuccess(msg) {
    console.log('✅', msg);
  }
};

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => ChatApp.init());
