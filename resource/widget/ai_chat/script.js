const pendingRequests = new Map();
function generateUniqueId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

function isContextLengthError(errorJson) {
  if (errorJson.error?.code === 'context_length_exceeded') {
    return true;
  }
  const message = (errorJson.error?.message || '').toLowerCase();
  const keywords = ['maximum context length', 'context length', 'context window', 'token limit', 'tokens exceed', 'too many tokens', 'requested too many tokens'];
  return keywords.some((keyword) => message.includes(keyword));
}

function cleanupRequest(requestId) {
  const request = pendingRequests.get(requestId);
  if (request && request.handler) {
    backend.toolResultReady.disconnect(request.handler);
  }
  pendingRequests.delete(requestId);
}

function setQQUserInfo(qq_name, qq_number) {
  let messageId = generateUniqueId();
  if (!window.ws) {
    return;
  }
  if (window.ws.readyState === WebSocket.CONNECTING) {
    return;
  }
  window.ws.send(JSON.stringify({ action: 'setQQUser', data: JSON.stringify({ qq_name, qq_number, id: messageId }) }));
  const avatarUrl = 'http://q.qlogo.cn/headimg_dl?dst_uin=' + qq_number + '&spec=640&img_type=png';
  window.currentUserInfo = { name: qq_name, avatarUrl: avatarUrl };
  document.querySelectorAll('.message-group.user').forEach((groupDiv) => {
    const iconSpan = groupDiv.querySelector(':scope > .icon');
    const senderDiv = groupDiv.querySelector('.message-sender');
    if (iconSpan) {
      iconSpan.innerHTML = `<img src="${avatarUrl}" style="width: 30px; height: 30px; border-radius: 50%;" />`;
    }
    if (senderDiv) {
      const nameDiv = senderDiv.querySelector('div');
      if (nameDiv) {
        nameDiv.textContent = qq_name;
      }
    }
  });
}
window.OnlineUser = {};
window.setQQUserInfo = setQQUserInfo;
window.currentUserInfo = { name: '用户', avatarUrl: null };

async function updateTokenUsage() {
  const tokenElement = document.getElementById('token-count');
  const rawCountStr = await backend.getTokenUsage(aiChatApiOptionsBody.messages);
  const num = parseInt(rawCountStr, 10);
  if (isNaN(num)) {
    tokenElement.textContent = rawCountStr;
    return;
  }
  let displayText = num.toString();
  if (num >= 1000000) {
    displayText += ` (${(num / 1000000).toFixed(1)}M)`;
  } else if (num >= 1000) {
    displayText += ` (${(num / 1000).toFixed(1)}K)`;
  }
  tokenElement.textContent = displayText;
}

async function executeMcpTool(serverName, toolName, args, providedRequestId = null) {
  return new Promise((resolve, reject) => {
    const requestId = providedRequestId || generateUniqueId();
    const handler = (receivedId, result) => {
      if (receivedId === requestId) {
        const request = pendingRequests.get(requestId);
        const wasCancelled = request && request.cancelled;
        cleanupRequest(requestId);
        try {
          const parsedResult = JSON.parse(result);
          if (parsedResult.status === 'cancelled') {
            if (wasCancelled) {
              resolve(result);
            } else {
              reject(new Error(parsedResult.content));
            }
          } else {
            resolve(result);
          }
        } catch (e) {
          resolve(result);
        }
      }
    };
    pendingRequests.set(requestId, {
      handler,
      reject,
      serverName,
      toolName,
      startTime: Date.now(),
    });
    backend.toolResultReady.connect(handler);
    try {
      backend.executeMcpTool(serverName, toolName, args, requestId);
    } catch (error) {
      cleanupRequest(requestId);
      reject(error);
    }
  });
}

function getPendingRequests() {
  const requests = [];
  for (const [id, info] of pendingRequests) {
    requests.push({
      id,
      tool: `${info.serverName}.${info.toolName}`,
      duration: Date.now() - info.startTime,
    });
  }
  return requests;
}

function cancelMcpRequest(requestId) {
  const request = pendingRequests.get(requestId);
  if (request) {
    request.cancelled = true;
    backend.cancelMcpTool(requestId);
  }
}
function copyToClipboard(text, buttonElement) {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.opacity = 0;
  document.body.appendChild(textarea);
  textarea.select();
  try {
    document.execCommand('copy');
    const originalTitle = buttonElement.title;
    buttonElement.title = '已复制!';
    setTimeout(() => {
      buttonElement.title = originalTitle;
    }, 2000);
  } catch (err) {
    console.error('Fallback: Oops, unable to copy', err);
    const originalTitle = buttonElement.title;
    buttonElement.title = '复制失败!';
    setTimeout(() => {
      buttonElement.title = originalTitle;
    }, 2000);
  }
  document.body.removeChild(textarea);
}
class ChatController {
  constructor(chatBodySelector) {
    this.chatBody = document.querySelector(chatBodySelector);
    if (!this.chatBody) {
      throw new Error(`Container element '${chatBodySelector}' not found.`);
    }
    this.userHasScrolled = false;
    this.chatBody.addEventListener('scroll', () => {
      const threshold = 15;
      const isAtBottom = this.chatBody.scrollHeight - this.chatBody.scrollTop - this.chatBody.clientHeight < threshold;
      this.userHasScrolled = !isAtBottom;
    });
  }
  scrollToBottom() {
    setTimeout(() => {
      this.chatBody.scrollTop = this.chatBody.scrollHeight;
    }, 100);
  }
  addUserBubble(text, imageUrls, messageIndex = -1, historyIndex = -1) {
    const bubble = new UserBubble(this.chatBody, messageIndex, historyIndex);
    bubble.setContent(text, imageUrls);
    this.userHasScrolled = false;
    this.scrollToBottom();
    return bubble;
  }
  addAIBubble(messageIndex = -1, historyIndex = -1) {
    const bubble = new AIBubble(this.chatBody, this, messageIndex, historyIndex);
    return bubble;
  }
  addSystemBubble(toolName, code, relatedMessageIndex = -1, historyIndex = -1) {
    const bubble = new SystemBubble(this.chatBody, relatedMessageIndex, historyIndex);
    bubble.setToolCall(toolName, code);
    return bubble;
  }
}
class UserBubble {
  constructor(container, messageIndex = -1, historyIndex = -1) {
    const senderName = window.currentUserInfo.name;
    const senderIcon = window.currentUserInfo.avatarUrl ? `<img src="${window.currentUserInfo.avatarUrl}" style="width:64px;height:64px; border-radius: 50%; object-fit: cover;" />` : '<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"></path></svg>';
    const template = `<div class="message-group user"${messageIndex >= 0 ? ` data-message-index="${messageIndex}"` : ''}${historyIndex >= 0 ? ` data-history-index="${historyIndex}"` : ''}>
              <div class="message-wrapper">
                <div class="message-sender">
                  <div class="message-actions">
                    <button class="copy-button" title="复制">
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/>
                        <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/>
                      </svg>
                    </button>
                    <button class="edit-button" title="编辑">
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325z"/>
                      </svg>
                    </button>
                    <button class="retry-button" title="重试">
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41zm-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9z"/>
                        <path fill-rule="evenodd" d="M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5.002 5.002 0 0 0 8 3zM3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9H3.1z"/>
                      </svg>
                    </button>
                    <button class="delete-button" title="删除">
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>
                        <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
                      </svg>
                    </button>
                  </div>
                  <div>${senderName}</div>
                </div>
                <div class="user-response"></div>
              </div>
              <span class="icon">${senderIcon}</span>
            </div>`;
    container.insertAdjacentHTML('beforeend', template);
    this.element = container.lastElementChild;
    this.contentElement = this.element.querySelector('.user-response');
    this.messageIndex = messageIndex;
    this.historyIndex = historyIndex;
    this.bindEventListeners();
  }
  bindEventListeners() {
    const copyBtn = this.element.querySelector('.copy-button');
    const editBtn = this.element.querySelector('.edit-button');
    const retryBtn = this.element.querySelector('.retry-button');
    const deleteBtn = this.element.querySelector('.delete-button');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        copyToClipboard(this.contentElement.textContent, copyBtn);
      });
    }
    if (editBtn) {
      editBtn.addEventListener('click', () => editUserMessage(this.element));
    }
    if (retryBtn) {
      retryBtn.addEventListener('click', () => retryUserMessage(this.element));
    }
    if (deleteBtn) {
      deleteBtn.addEventListener('click', () => deleteUserMessage(this.element));
    }
  }
  setContent(text, imageUrls) {
    this.contentElement.innerHTML = '';
    if (text) {
      const textBlock = document.createElement('div');
      textBlock.className = 'user-text-block';
      textBlock.textContent = text;
      this.contentElement.appendChild(textBlock);
    }
    if (imageUrls && imageUrls.length > 0) {
      const imageContainer = document.createElement('div');
      imageContainer.style.display = 'flex';
      imageContainer.style.flexWrap = 'wrap';
      imageContainer.style.gap = '10px';
      imageContainer.style.marginTop = text ? '10px' : '0';
      imageUrls.forEach((url) => {
        const img = document.createElement('img');
        img.src = url;
        img.style.maxWidth = '150px';
        img.style.maxHeight = '150px';
        img.style.borderRadius = '8px';
        img.style.objectFit = 'cover';
        imageContainer.appendChild(img);
      });
      this.contentElement.appendChild(imageContainer);
    }
  }
}
class AIBubble {
  constructor(container, chatController, messageIndex = -1, historyIndex = -1) {
    const template = `<div class="message-group ai"${messageIndex >= 0 ? ` data-message-index="${messageIndex}"` : ''}${historyIndex >= 0 ? ` data-history-index="${historyIndex}"` : ''}>
              <div class="message-sender">
                <span class="icon">💬</span>
                <div>智能助手</div>
                <div class="message-actions">
                  <button class="copy-button" title="复制">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                      <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/>
                      <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/>
                    </svg>
                  </button>
                  <button class="retry-button" title="重试">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                      <path d="M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41zm-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9z"/>
                      <path fill-rule="evenodd" d="M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5.002 5.002 0 0 0 8 3zM3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9H3.1z"/>
                    </svg>
                  </button>
                  <button class="delete-button" title="删除">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                      <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>
                      <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
                    </svg>
                  </button>
                </div>
              </div>
              <div class="message-content"></div>
            </div>`;
    container.insertAdjacentHTML('beforeend', template);
    this.element = container.lastElementChild;
    this.contentElement = this.element.querySelector('.message-content');
    this.fullContent = '';
    this.isStreaming = false;
    this.chatController = chatController;
    this.messageIndex = messageIndex;
    this.historyIndex = historyIndex;
    this.bindEventListeners();
  }
  bindEventListeners() {
    const copyBtn = this.element.querySelector('.copy-button');
    const retryBtn = this.element.querySelector('.retry-button');
    const deleteBtn = this.element.querySelector('.delete-button');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        copyToClipboard(this.fullContent, copyBtn);
      });
    }
    if (retryBtn) {
      retryBtn.addEventListener('click', () => retryAIMessage(this.element));
    }
    if (deleteBtn) {
      deleteBtn.addEventListener('click', () => deleteAIMessage(this.element));
    }
  }
  getHtml() {
    return this.contentElement.innerHTML;
  }
  setHTML(markdown) {
    if (isEmptyObject(markdown)) {
      return;
    }
    try {
      this.isStreaming = false;
      this.fullContent = markdown;
      const dirtyHtml = marked.parse(markdown);
      const cleanHtml = DOMPurify.sanitize(dirtyHtml);
      this.contentElement.innerHTML = cleanHtml;
      if (this.chatController && !this.chatController.userHasScrolled) {
        this.chatController.scrollToBottom();
      }
    } catch (e) {
      console.log(e);
      debugger;
      throw new Error('setHTML error');
    }
  }
  updateStream(chunk) {
    if (!this.isStreaming) {
      this.isStreaming = true;
      this.fullContent = '';
    }
    this.fullContent += chunk;
    const dirtyHtml = marked.parse(this.fullContent);
    const cleanHtml = DOMPurify.sanitize(dirtyHtml);
    this.contentElement.innerHTML = cleanHtml + '<div class="loader"></div>';
    if (this.chatController && !this.chatController.userHasScrolled) {
      this.chatController.scrollToBottom();
    }
  }
  finishStream() {
    this.isStreaming = false;
    const dirtyHtml = marked.parse(this.fullContent);
    const cleanHtml = DOMPurify.sanitize(dirtyHtml);
    this.contentElement.innerHTML = cleanHtml;
    if (this.chatController && !this.chatController.userHasScrolled) {
      this.chatController.scrollToBottom();
    }
  }
}
class SystemBubble {
  constructor(container, relatedMessageIndex = -1, historyIndex = -1) {
    const template = `<div class="message-group system"${relatedMessageIndex >= 0 ? ` data-related-message-index="${relatedMessageIndex}"` : ''}${historyIndex >= 0 ? ` data-history-index="${historyIndex}"` : ''}>
              <div class="tool-call-card">
                <div class="tool-call-header">
                  <span class="tool-name"></span>
                  <div class="tool-status-icon"><div class="loader"></div></div>
                </div>
                <div class="tool-call-body">
                  <div class="code-block"></div>
                </div>
                <div class="tool-call-result" style="display: none;">
                  <div class="code-block"></div>
                </div>
              </div>
            </div>`;
    container.insertAdjacentHTML('beforeend', template);
    this.element = container.lastElementChild;
    this.toolCardElement = this.element.querySelector('.tool-call-card');
    this.toolNameElement = this.element.querySelector('.tool-name');
    this.detailElement = this.element.querySelector('.tool-call-body .code-block');
    this.bodyContainer = this.element.querySelector('.tool-call-body');
    this.resultContainer = this.element.querySelector('.tool-call-result');
    this.resultContentElement = this.element.querySelector('.tool-call-result .code-block');
    this.headerElement = this.element.querySelector('.tool-call-header');
    this.statusIconElement = this.element.querySelector('.tool-status-icon');
  }
  isDangerousTool(toolName, detail) {
    if (!toolName.toLowerCase().includes('exe_shell')) {
      return [];
    }
    const dangerousCommands = ['rm', 'chmod', 'mv', 'killall', 'kill', 'mkfs'];
    let argsXml = detail;
    let shellCommand = '';
    try {
      argsXml = JSON.parse(detail);
      const shellMatch = argsXml.match(/<shell>([\s\S]*?)<\/shell>/);
      if (shellMatch && shellMatch[1]) {
        shellCommand = shellMatch[1];
      } else {
        return [];
      }
    } catch (e) {
      return [];
    }
    const foundCommands = new Set();
    const regex = new RegExp(`\\b(${dangerousCommands.join('|')})\\b`, 'gi');
    let match;
    while ((match = regex.exec(shellCommand)) !== null) {
      foundCommands.add(match[0].toLowerCase());
    }
    return Array.from(foundCommands);
  }
  _prettyPrintXml(xml) {
    const PADDING = '  ';
    const reg = /(>)(<)(\/*)/g;
    let pad = 0;
    xml = xml.replace(reg, '$1\n$2$3');
    return xml
      .split('\n')
      .map((node) => {
        let indent = 0;
        if (node.match(/.+<\/\w[^>]*>$/)) {
          indent = 0;
        } else if (node.match(/^<\/\w/)) {
          if (pad !== 0) {
            pad -= 1;
          }
        } else if (node.match(/^<\w[^>]*[^\/]>.*$/)) {
          indent = 1;
        }
        const padding = PADDING.repeat(pad);
        pad += indent;
        return padding + node;
      })
      .join('\n');
  }
  _formatAndHighlight(code) {
    let content = code.trim();
    if (content.startsWith('"') && content.endsWith('"')) {
      content = content.substring(1, content.length - 1);
    }
    try {
      const jsonObj = JSON.parse(content);
      const formatted = JSON.stringify(jsonObj, null, 2);
      return hljs.highlight(formatted, { language: 'json' }).value;
    } catch (e) {}
    const trimmedContent = content.trim();
    if (trimmedContent.startsWith('<') && trimmedContent.endsWith('>')) {
      const unescapedContent = content.replace(/\\n/g, '\n');
      const formattedXml = this._prettyPrintXml(unescapedContent);
      return hljs.highlight(formattedXml, { language: 'xml' }).value;
    }
    return hljs.highlight(code, { language: 'plaintext' }).value;
  }
  setToolCall(toolName, detail) {
    this.toolNameElement.textContent = toolName;
    const dangerousCmds = this.isDangerousTool(toolName, detail);
    if (toolName.toLowerCase().includes('exe_shell') && dangerousCmds.length > 0) {
      this.toolCardElement.classList.add('dangerous');
      this.toolNameElement.innerHTML = '⚠️ ' + this.toolNameElement.textContent;
      try {
        let argsXml = JSON.parse(detail);
        const shellMatch = argsXml.match(/<shell>([\s\S]*?)<\/shell>/);
        const cwdMatch = argsXml.match(/<cwd>([\s\S]*?)<\/cwd>/);
        if (shellMatch) {
          const fullCommand = shellMatch[1];
          const escapedCmds = dangerousCmds.map((cmd) => cmd.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
          const regex = new RegExp(`(\\b(?:${escapedCmds.join('|')})\\b)`, 'gi');
          const parts = fullCommand.split(regex);
          this.detailElement.innerHTML = '';
          this.detailElement.appendChild(document.createTextNode('<exe_shell>\n  <shell>'));
          parts.forEach((part) => {
            if (part) {
              if (dangerousCmds.includes(part.toLowerCase())) {
                const dangerousSpan = document.createElement('span');
                dangerousSpan.className = 'dangerous-command';
                dangerousSpan.textContent = part;
                this.detailElement.appendChild(dangerousSpan);
              } else {
                this.detailElement.appendChild(document.createTextNode(part));
              }
            }
          });
          this.detailElement.appendChild(document.createTextNode('</shell>'));
          if (cwdMatch) {
            this.detailElement.appendChild(document.createTextNode(`\n  <cwd>${cwdMatch[1]}</cwd>`));
          }
          this.detailElement.appendChild(document.createTextNode('\n</exe_shell>'));
        } else {
          this.detailElement.innerHTML = this._formatAndHighlight(detail);
        }
      } catch (e) {
        this.detailElement.innerHTML = this._formatAndHighlight(detail);
      }
    } else {
      this.detailElement.innerHTML = this._formatAndHighlight(detail);
    }
  }
  setResult(status, content) {
    this.statusIconElement.innerHTML = '';
    this.bodyContainer.style.display = 'none';
    if (status === 'approved') {
      this.resultContentElement.innerHTML = this._formatAndHighlight(content);
      this.statusIconElement.textContent = '▼';
      this.statusIconElement.classList.add('success');
      this.headerElement.addEventListener('click', () => {
        const isCollapsed = this.bodyContainer.style.display === 'none';
        const hasResult = this.resultContentElement.textContent.trim() !== '';
        if (isCollapsed) {
          this.bodyContainer.style.display = 'block';
          if (hasResult) {
            this.resultContainer.style.display = 'block';
          }
          this.statusIconElement.textContent = '▲';
        } else {
          this.bodyContainer.style.display = 'none';
          this.resultContainer.style.display = 'none';
          this.statusIconElement.textContent = '▼';
        }
      });
    } else if (status === 'rejected') {
      this.statusIconElement.textContent = '❌';
      this.resultContainer.style.display = 'none';
      this.headerElement.addEventListener('click', () => {
        const isHidden = this.bodyContainer.style.display === 'none';
        this.bodyContainer.style.display = isHidden ? 'block' : 'none';
      });
    }
  }
  async requireApproval() {
    return new Promise((resolve) => {
      const approvalContainer = document.getElementById('approve-reject-buttons');
      const approveBtn = approvalContainer.querySelector('.cmd-button');
      const rejectBtn = approvalContainer.querySelector('.reject-button');
      approvalContainer.style.display = 'flex';
      const cleanup = () => {
        approvalContainer.style.display = 'none';
        approveBtn.replaceWith(approveBtn.cloneNode(true));
        rejectBtn.replaceWith(rejectBtn.cloneNode(true));
      };
      approveBtn.addEventListener(
        'click',
        () => {
          cleanup();
          resolve('approved');
        },
        { once: true },
      );
      rejectBtn.addEventListener(
        'click',
        () => {
          cleanup();
          resolve('rejected');
        },
        { once: true },
      );
    });
  }
}
let pastedImageDataUrls = [];
function editUserMessage(bubbleElement) {
  const messageIndex = parseInt(bubbleElement.dataset.messageIndex);
  const historyIndex = parseInt(bubbleElement.dataset.historyIndex);
  if (isNaN(historyIndex) || historyIndex < 0) {
    console.error('Invalid history index');
    return;
  }
  const messageItem = window.messagesHistory[historyIndex];
  if (!messageItem || messageItem.messages.role !== 'user' || messageItem.isMcp) {
    console.error('Can only edit user messages');
    return;
  }
  const messageContent = messageItem.messages.content;
  let text = '';
  let images = [];
  if (Array.isArray(messageContent)) {
    messageContent.forEach((item) => {
      if (item.type === 'text') {
        if (!item.text.startsWith('<附加系统数据>')) {
          text = item.text || '';
        }
      } else if (item.type === 'image_url' && item.image_url) {
        images.push(item.image_url.url);
      }
    });
  } else if (typeof messageContent === 'string') {
    text = messageContent;
  }
  truncateFromMessage(messageIndex, historyIndex);
  const messageInput = document.querySelector('#message-input');
  if (messageInput) {
    messageInput.textContent = text;
    highlightMentions(messageInput);
  }
  pastedImageDataUrls = [...images];
  renderImagePreviews();
  if (messageInput) {
    messageInput.focus();
  }
}
function retryUserMessage(bubbleElement) {
  editUserMessage(bubbleElement);
  setTimeout(() => {
    const sendButton = document.querySelector('.send-button');
    if (sendButton) {
      sendButton.click();
    }
  }, 100);
}
function deleteUserMessage(bubbleElement) {
  const messageIndex = parseInt(bubbleElement.dataset.messageIndex);
  const historyIndex = parseInt(bubbleElement.dataset.historyIndex);
  if (isNaN(historyIndex) || historyIndex < 0) {
    console.error('Invalid history index');
    return;
  }
  const messageItem = window.messagesHistory[historyIndex];
  if (!messageItem || messageItem.messages.role !== 'user' || messageItem.isMcp) {
    console.error('Can only delete user messages');
    return;
  }
  truncateFromMessage(messageIndex, historyIndex);
}
function truncateFromMessage(messageIndex, historyIndex) {
  if (!isNaN(messageIndex) && messageIndex >= 0) {
    const hasSystemMessage = aiChatApiOptionsBody.messages.length > 0 && aiChatApiOptionsBody.messages[0].role === 'system';
    if (hasSystemMessage) {
      aiChatApiOptionsBody.messages = aiChatApiOptionsBody.messages.slice(0, messageIndex);
    } else {
      const actualIndex = messageIndex - 1;
      if (actualIndex >= 0) {
        aiChatApiOptionsBody.messages = aiChatApiOptionsBody.messages.slice(0, actualIndex);
      } else {
        aiChatApiOptionsBody.messages = [];
      }
    }
  }
  window.messagesHistory = window.messagesHistory.slice(0, historyIndex);
  const bubblesToRemove = document.querySelectorAll('[data-history-index]');
  bubblesToRemove.forEach((bubble) => {
    const bubbleHistoryIndex = parseInt(bubble.dataset.historyIndex);
    if (bubbleHistoryIndex >= historyIndex) {
      bubble.remove();
    }
  });
  if (typeof window.saveHistory === 'function' && window.firstUserMessage) {
    window.saveHistory(window.firstUserMessage, window.messagesHistory);
  }
}
function createAIResponseHandler(aiBubble, messageOffset, aiMessageIndex, aiHistoryIndex, controller, onComplete) {
  updateTokenUsage();
  const cancelButtonContainer = document.getElementById('cancel-button-container');
  const cancelButton = cancelButtonContainer.querySelector('.cancel-button');
  const sendButton = document.querySelector('.send-button');
  return async (fullContent) => {
    aiBubble.finishStream();
    const assistantMessage = {
      role: 'assistant',
      content: fullContent,
    };
    aiChatApiOptionsBody.messages.push(assistantMessage);
    messagesHistory.push({ messages: assistantMessage, isMcp: false });
    saveHistory(window.firstUserMessage, messagesHistory);
    cancelButtonContainer.style.display = 'none';
    if (backend) {
      const result = await backend.processMessage(fullContent);
      if (result) {
        try {
          const toolCall = JSON.parse(result);
          if (toolCall && toolCall.server_name && toolCall.tool_name && toolCall.arguments) {
            let xml = toolCall._xml_;
            if (xml) {
              let newContent = fullContent.replace(xml, '');
              if (newContent == '') {
                newContent = toolCall.server_name + ' -> ' + toolCall.tool_name;
              }
              aiBubble.setHTML(newContent);
            }
            const toolName = `${toolCall.server_name} -> ${toolCall.tool_name}`;
            const toolArgsStr = JSON.stringify(toolCall.arguments, null, 2);
            const systemBubble = chat.addSystemBubble(toolName, toolArgsStr, aiMessageIndex, aiHistoryIndex);
            let userDecision = 'rejected';
            if (toolCall['auto_approve'] === true) {
              userDecision = 'approved';
            } else {
              userDecision = await systemBubble.requireApproval();
            }
            if (userDecision === 'approved') {
              const toolRequestId = generateUniqueId();
              const abortHandler = () => {
                cancelButtonContainer.style.display = 'none';
                cancelMcpRequest(toolRequestId);
              };
              cancelButton.addEventListener('click', abortHandler);
              const continueButton = cancelButtonContainer.querySelector('.continue-button');
              const continueHandler = () => {
                backend.forceContinueTool(toolRequestId);
              };
              continueButton.addEventListener('click', continueHandler, { once: true });
              if (toolCall.tool_name === 'exe_shell') {
                continueButton.style.display = 'block';
              } else {
                continueButton.style.display = 'none';
              }
              cancelButtonContainer.style.display = 'flex';
              sendButton.disabled = true;
              try {
                const executionResultStr = await executeMcpTool(toolCall.server_name, toolCall.tool_name, JSON.stringify(toolCall.arguments), toolRequestId);
                systemBubble.setResult('approved', executionResultStr);
                let mcpMessages = {
                  role: 'user',
                  content: [
                    { type: 'text', text: '[' + toolCall.server_name + ' -> ' + toolCall.tool_name + '] 执行结果:' },
                    { type: 'text', text: executionResultStr },
                  ],
                };
                aiChatApiOptionsBody.messages.push(mcpMessages);
                messagesHistory.push({ messages: mcpMessages, isMcp: true });
                saveHistory(window.firstUserMessage, messagesHistory);
                cancelButton.removeEventListener('click', abortHandler);
                continueButton.removeEventListener('click', continueHandler);
                const newController = new AbortController();
                const newAbortHandler = () => {
                  cancelButtonContainer.style.display = 'none';
                  newController.abort();
                };
                cancelButton.addEventListener('click', newAbortHandler);
                const newOnComplete = () => {
                  cancelButton.removeEventListener('click', newAbortHandler);
                  if (onComplete) {
                    onComplete();
                  }
                };
                const newAiMessageIndex = aiChatApiOptionsBody.messages.length + messageOffset;
                const newAiHistoryIndex = messagesHistory.length;
                const newAiBubble = chat.addAIBubble(newAiMessageIndex, newAiHistoryIndex);
                newAiBubble.updateStream('');
                const newHandler = createAIResponseHandler(newAiBubble, messageOffset, newAiMessageIndex, newAiHistoryIndex, newController, newOnComplete);
                if (continueButton) {
                  continueButton.style.display = 'none';
                }
                requestAiChat(newAiBubble.updateStream.bind(newAiBubble), newHandler, newController.signal);
                return;
              } catch (error) {
                systemBubble.setResult('rejected', `执行已取消:${error.message}`);
                cancelButtonContainer.style.display = 'none';
                if (onComplete) {
                  onComplete();
                }
              } finally {
                cancelButton.removeEventListener('click', abortHandler);
                continueButton.removeEventListener('click', continueHandler);
              }
            } else {
              systemBubble.setResult('rejected', 'User rejected the tool call.');
            }
          }
        } catch (e) {
          console.error('Failed to process or execute MCP tool call:', e);
        }
      }
    }
    if (onComplete) {
      onComplete();
    }
  };
}
function retryAIMessage(bubbleElement) {
  const messageIndex = parseInt(bubbleElement.dataset.messageIndex);
  const historyIndex = parseInt(bubbleElement.dataset.historyIndex);
  if (isNaN(historyIndex) || historyIndex < 0) {
    console.error('Invalid history index');
    return;
  }
  const messageItem = window.messagesHistory[historyIndex];
  if (!messageItem || messageItem.messages.role !== 'assistant') {
    console.error('Can only retry AI messages');
    return;
  }
  const sendButton = document.querySelector('.send-button');
  if (sendButton && sendButton.disabled) {
    console.log('Another request is in progress');
    return;
  }
  truncateFromMessage(messageIndex, historyIndex);
  const hasSystemMessage = aiChatApiOptionsBody.messages.length > 0 && aiChatApiOptionsBody.messages[0].role === 'system';
  const messageOffset = hasSystemMessage ? 0 : 1;
  const aiMessageIndex = aiChatApiOptionsBody.messages.length + messageOffset;
  const aiHistoryIndex = messagesHistory.length;
  let aiBubble = chat.addAIBubble(aiMessageIndex, aiHistoryIndex);
  aiBubble.updateStream('');
  sendButton.disabled = true;
  chat.chatBody.classList.add('request-in-progress');
  const cancelButtonContainer = document.getElementById('cancel-button-container');
  const controller = new AbortController();
  const cancelButton = cancelButtonContainer.querySelector('.cancel-button');
  const abortRequest = () => {
    cancelButtonContainer.style.display = 'none';
    controller.abort();
  };
  cancelButton.addEventListener('click', abortRequest);
  const continueButton = cancelButtonContainer.querySelector('.continue-button');
  continueButton.style.display = 'none';
  cancelButtonContainer.style.display = 'flex';
  const onComplete = () => {
    sendButton.disabled = false;
    chat.chatBody.classList.remove('request-in-progress');
    cancelButton.removeEventListener('click', abortRequest);
    if (chat.chatController && !chat.chatController.userHasScrolled) {
      chat.chatController.scrollToBottom();
    }
  };
  const responseHandler = createAIResponseHandler(aiBubble, messageOffset, aiMessageIndex, aiHistoryIndex, controller, onComplete);
  requestAiChat(aiBubble.updateStream.bind(aiBubble), responseHandler, controller.signal);
}
function deleteAIMessage(bubbleElement) {
  const messageIndex = parseInt(bubbleElement.dataset.messageIndex);
  const historyIndex = parseInt(bubbleElement.dataset.historyIndex);
  if (isNaN(historyIndex) || historyIndex < 0) {
    console.error('Invalid history index');
    return;
  }
  const messageItem = window.messagesHistory[historyIndex];
  if (!messageItem || messageItem.messages.role !== 'assistant') {
    console.error('Can only delete AI messages');
    return;
  }
  truncateFromMessage(messageIndex, historyIndex);
}
function isEmptyObject(obj) {
  const isPlainObject = Object.prototype.toString.call(obj) === '[object Object]';
  if (!isPlainObject) {
    return false;
  }
  return Object.keys(obj).length === 0;
}
function renderImagePreviews() {
  const inputArea = document.querySelector('.input-area');
  let previewContainer = document.getElementById('image-preview-container');
  if (pastedImageDataUrls.length === 0) {
    if (previewContainer) {
      previewContainer.remove();
    }
    return;
  }
  if (!previewContainer) {
    previewContainer = document.createElement('div');
    previewContainer.id = 'image-preview-container';
    inputArea.parentNode.insertBefore(previewContainer, inputArea.nextSibling);
  }
  previewContainer.style.display = 'flex';
  previewContainer.style.overflowX = 'auto';
  previewContainer.style.overflowY = 'hidden';
  previewContainer.style.gap = '10px';
  previewContainer.style.padding = '10px 0';
  previewContainer.style.width = '100%';
  previewContainer.innerHTML = '';
  pastedImageDataUrls.forEach((dataUrl, index) => {
    const imageWrapper = document.createElement('div');
    imageWrapper.style.position = 'relative';
    imageWrapper.style.flexShrink = '0';
    const img = document.createElement('img');
    img.src = dataUrl;
    img.style.width = '80px';
    img.style.height = '80px';
    img.style.borderRadius = '8px';
    img.style.objectFit = 'cover';
    img.style.display = 'block';
    const removeBtn = document.createElement('button');
    removeBtn.textContent = '×';
    removeBtn.style.position = 'absolute';
    removeBtn.style.top = '-5px';
    removeBtn.style.right = '-5px';
    removeBtn.style.background = 'rgba(0,0,0,0.7)';
    removeBtn.style.color = 'white';
    removeBtn.style.border = '1px solid white';
    removeBtn.style.borderRadius = '50%';
    removeBtn.style.cursor = 'pointer';
    removeBtn.style.width = '20px';
    removeBtn.style.height = '20px';
    removeBtn.style.lineHeight = '18px';
    removeBtn.style.textAlign = 'center';
    removeBtn.style.padding = '0';
    removeBtn.style.fontSize = '16px';
    removeBtn.style.fontWeight = 'bold';
    removeBtn.onclick = () => {
      pastedImageDataUrls.splice(index, 1);
      renderImagePreviews();
    };
    imageWrapper.appendChild(img);
    imageWrapper.appendChild(removeBtn);
    previewContainer.appendChild(imageWrapper);
  });
}
function highlightMentions(inputElement) {
  const text = inputElement.textContent;
  const mentionRegex = /\s@([a-zA-Z]+:[^\s]+)\s/g;
  const matches = [];
  let match;
  while ((match = mentionRegex.exec(text)) !== null) {
    matches.push({
      start: match.index + 1,
      end: match.index + match[0].length - 1,
      mention: match[0].trim(),
    });
  }
  if (matches.length === 0) return;
  let html = '';
  let lastIndex = 0;
  matches.forEach((m) => {
    html += text.substring(lastIndex, m.start).replace(/</g, '<').replace(/>/g, '>');
    html += `<span class="mention-tag" contenteditable="false">${m.mention}</span>`;
    lastIndex = m.end;
  });
  html += text.substring(lastIndex).replace(/</g, '<').replace(/>/g, '>');
  inputElement.innerHTML = html;
  const range = document.createRange();
  const sel = window.getSelection();
  range.selectNodeContents(inputElement);
  range.collapse(false);
  sel.removeAllRanges();
  sel.addRange(range);
}
function handlePaste(event) {
  event.preventDefault();
  const clipboardData = event.clipboardData || window.clipboardData;
  const items = clipboardData.items;
  let imageFound = false;
  for (const item of items) {
    if (item.kind === 'file' && item.type.startsWith('image/')) {
      imageFound = true;
      const file = item.getAsFile();
      const reader = new FileReader();
      reader.onload = function (e) {
        pastedImageDataUrls.push(e.target.result);
        renderImagePreviews();
      };
      reader.readAsDataURL(file);
    }
  }
  if (!imageFound) {
    const plainText = clipboardData.getData('text/plain');
    if (plainText) {
      const selection = window.getSelection();
      if (!selection.rangeCount) return;
      selection.deleteFromDocument();
      const range = selection.getRangeAt(0);
      range.deleteContents();
      const textNode = document.createTextNode(plainText);
      range.insertNode(textNode);
      range.setStartAfter(textNode);
      range.collapse(true);
      selection.removeAllRanges();
      selection.addRange(range);
      event.target.focus();
      event.target.scrollTop = event.target.scrollHeight;
      highlightMentions(event.target);
    }
  }
}
window.messagesHistory = [];
let aiChatApiOptionsBody = {
  model: '',
  temperature: 0.6,
  messages: [],
  stream: true,
  stream_options: {
    include_usage: true,
  },
};
window.firstUserMessage = '';
let backend;
let lastSystemData = {};
const chat = new ChatController('.chat-body');
const chatHistoryContainer = document.querySelector('.chat-history');
window.loadHistory = function (filename) {
  initializeBackendConnection(async (backend) => {
    if (!backend) {
      return;
    }
    const history = await backend.loadHistory(filename);
    if (!history) {
      return;
    }
    chatHistoryContainer.style.display = 'none';
    window.firstUserMessage = filename.replace('.json', '');
    window.messagesHistory = JSON.parse(history);
    chat.chatBody.innerHTML = '';
    let messageIndexOffset = 0;
    for (let i = 0; i < window.messagesHistory.length; i++) {
      const item = window.messagesHistory[i];
      aiChatApiOptionsBody.messages.push(item.messages);
      if (i === 0 && item.messages.role === 'system') {
        messageIndexOffset = 0;
        continue;
      } else if (i === 0) {
        messageIndexOffset = 1;
      }
      const messageIndex = aiChatApiOptionsBody.messages.length - 1 + messageIndexOffset;
      if (item.messages.role === 'user') {
        if (item.isMcp) {
          continue;
        }
        let userText = '';
        let imageUrls = [];
        if (Array.isArray(item.messages.content)) {
          item.messages.content.forEach((contentPart) => {
            if (contentPart.type === 'text') {
              const text = contentPart.text || '';
              if (!text.startsWith('<附加系统数据>')) {
                userText += text;
              }
            } else if (contentPart.type === 'image_url' && contentPart.image_url) {
              imageUrls.push(contentPart.image_url.url);
            }
          });
        } else {
          userText = item.messages.content;
        }
        chat.addUserBubble(userText, imageUrls, messageIndex, i);
      } else if (item.messages.role === 'assistant') {
        const aiBubble = chat.addAIBubble(messageIndex, i);
        let aiContent = item.messages.content;
        aiBubble.setHTML(aiContent);
        const result = await backend.processMessage(aiContent);
        if (result) {
          try {
            const toolCall = JSON.parse(result);
            if (toolCall && toolCall.server_name && toolCall.tool_name && toolCall.arguments) {
              let xml = toolCall._xml_;
              if (xml) {
                let newContent = aiContent.replace(xml, '');
                if (newContent == '') {
                  newContent = toolCall.server_name + ' -> ' + toolCall.tool_name;
                }
                aiBubble.setHTML(newContent);
              }
              const toolName = `${toolCall.server_name} -> ${toolCall.tool_name}`;
              const toolArgsStr = JSON.stringify(toolCall.arguments, null, 2);
              const systemBubble = chat.addSystemBubble(toolName, toolArgsStr, messageIndex, i);
              const nextItem = i + 1 < window.messagesHistory.length ? window.messagesHistory[i + 1] : null;
              if (nextItem && nextItem.isMcp === true) {
                let resultText = '';
                if (Array.isArray(nextItem.messages.content) && nextItem.messages.content.length > 1 && nextItem.messages.content[1].type === 'text') {
                  resultText = nextItem.messages.content[1].text || '';
                } else {
                  resultText = nextItem.messages.content.map((c) => c.text || '').join('\n');
                }
                systemBubble.setResult('approved', resultText);
              } else {
                systemBubble.setResult('rejected', '用户拒绝了工具调用.');
              }
            }
          } catch (e) {
            console.error('Failed to process tool call from history:', e);
          }
        }
      }
    }
    chat.scrollToBottom();
    updateTokenUsage();
  });
};
function initializeBackendConnection(callback) {
  if (backend) {
    if (callback) {
      callback(backend);
    }
    return;
  }
  if (typeof qt !== 'undefined' && typeof qt.webChannelTransport !== 'undefined') {
    new QWebChannel(qt.webChannelTransport, (channel) => {
      backend = channel.objects.backend;
      if (backend) {
        updateModelTags();
        if (callback) {
          callback(backend);
        }
      }
    });
  } else {
    console.error('QWebChannel transport not available.');
  }
}
document.addEventListener('DOMContentLoaded', function () {
  const attrDataStrPlugin = {
    'after:highlight': (result) => {
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = result.value;
      const elements = tempDiv.querySelectorAll('.hljs-attr, .hljs-name');
      elements.forEach((el) => {
        const text = el.textContent;
        if (el.classList.contains('hljs-attr')) {
          if (text.startsWith('"') && text.endsWith('"')) {
            const dataStr = text.substring(1, text.length - 1);
            el.setAttribute('data-str', dataStr);
          }
        } else if (el.classList.contains('hljs-name')) {
          el.setAttribute('data-str', text);
        }
      });
      const pathKeys = tempDiv.querySelectorAll('[data-str="path"]');
      pathKeys.forEach((keyEl) => {
        if (keyEl.classList.contains('hljs-attr')) {
          let currentNode = keyEl;
          while ((currentNode = currentNode.nextSibling)) {
            if (currentNode.nodeType === Node.ELEMENT_NODE) {
              if (currentNode.classList.contains('hljs-string')) {
                currentNode.classList.add('path-value');
                break;
              }
              if (currentNode.classList.contains('hljs-attr')) {
                break;
              }
            }
          }
        } else if (keyEl.classList.contains('hljs-name')) {
          const tagWrapper = keyEl.parentElement;
          if (tagWrapper && tagWrapper.classList.contains('hljs-tag')) {
            let valueNode = tagWrapper.nextSibling;
            if (valueNode && valueNode.nodeType === Node.TEXT_NODE && valueNode.textContent.trim() === '') {
              valueNode = valueNode.nextSibling;
            }
            if (valueNode && valueNode.nodeType === Node.TEXT_NODE && valueNode.textContent.trim() !== '') {
              const span = document.createElement('span');
              span.className = 'path-value';
              span.textContent = valueNode.textContent;
              valueNode.parentNode.replaceChild(span, valueNode);
            }
          }
        }
      });
      result.value = tempDiv.innerHTML;
    },
  };
  hljs.addPlugin(attrDataStrPlugin);
  marked.setOptions({
    highlight: function (code, lang) {
      const language = hljs.getLanguage(lang) ? lang : 'plaintext';
      return hljs.highlight(code, { language }).value;
    },
    langPrefix: 'hljs language-',
  });
  const messageInput = document.querySelector('#message-input');
  const sendButton = document.querySelector('.send-button');
  let isRequesting = false;
  function highlightMentions(inputElement) {
    const text = inputElement.textContent;
    const mentionRegex = /(\s)(@([a-zA-Z]+:[^\s]+))/g;
    let html = text.replace(mentionRegex, (match, space, mention) => {
      return `${space}<span class="mention-tag" contenteditable="false">${mention}</span>`;
    });
    if (inputElement.innerHTML !== html) {
      inputElement.innerHTML = html;
      const range = document.createRange();
      const sel = window.getSelection();
      range.selectNodeContents(inputElement);
      range.collapse(false);
      sel.removeAllRanges();
      sel.addRange(range);
    }
  }
  function _sanitize_filename(name) {
    name = name.replace(/[\\/*?:"<>|]/g, '');
    name = name.replace('\n', '').replace('\t', '').replace('\r', '');
    return name.substring(0, 16);
  }
  async function sendMessage() {
    let sshCwd = JSON.parse(await backend.get_current_cwd()).cwd;
    let fileManagerCwd = JSON.parse(await backend.get_file_manager_cwd()).cwd;
    let systemInfo = JSON.stringify(JSON.parse(await backend.get_system_info()).content);
    const approvalContainer = document.getElementById('approve-reject-buttons');
    if (approvalContainer && approvalContainer.style.display === 'flex') {
      const rejectBtn = approvalContainer.querySelector('.reject-button');
      if (rejectBtn) {
        rejectBtn.click();
        await new Promise((resolve) => setTimeout(resolve, 200));
      }
    }
    if (isRequesting) {
      return;
    }
    const message = messageInput.textContent;
    if (message || pastedImageDataUrls.length > 0) {
      chatHistoryContainer.style.display = 'none';
      if (window.firstUserMessage === '') {
        window.firstUserMessage = _sanitize_filename(message) + '_' + Date.now().toString();
      }
      isRequesting = true;
      sendButton.disabled = true;
      chat.chatBody.classList.add('request-in-progress');
      const hasSystemMessage = aiChatApiOptionsBody.messages.length > 0 && aiChatApiOptionsBody.messages[0].role === 'system';
      const messageOffset = hasSystemMessage ? 0 : 1;
      const currentMessageIndex = aiChatApiOptionsBody.messages.length + messageOffset;
      const currentHistoryIndex = messagesHistory.length;
      chat.addUserBubble(message, [...pastedImageDataUrls], currentMessageIndex, currentHistoryIndex);
      const userMessageContent = [];
      if (message) {
        userMessageContent.push({
          type: 'text',
          text: message,
        });
      }
      if (pastedImageDataUrls.length > 0) {
        pastedImageDataUrls.forEach((dataUrl) => {
          userMessageContent.push({
            type: 'image_url',
            image_url: {
              url: dataUrl,
            },
          });
        });
      }
      const currentSystemData = { sshCwd, fileManagerCwd, systemInfo };
      const systemDataMap = {
        sshCwd: '终端cwd',
        fileManagerCwd: '文件管理器cwd',
        systemInfo: '系统信息',
      };
      const changedDataXmlParts = [];
      for (const key in systemDataMap) {
        if (currentSystemData[key] !== lastSystemData[key]) {
          const tagName = systemDataMap[key];
          const value = currentSystemData[key];
          changedDataXmlParts.push(`<${tagName}>${value}</${tagName}>`);
        }
      }
      if (changedDataXmlParts.length > 0) {
        const systemDataXml = `<附加系统数据>\n${changedDataXmlParts.join('\n')}\n</附加系统数据>`;
        userMessageContent.push({
          type: 'text',
          text: systemDataXml,
        });
        Object.assign(lastSystemData, currentSystemData);
      }
      const userMessage = {
        role: 'user',
        content: userMessageContent,
      };
      aiChatApiOptionsBody.messages.push(userMessage);
      messagesHistory.push({ messages: userMessage, isMcp: false });
      saveHistory(window.firstUserMessage, messagesHistory);
      updateTokenUsage();
      pastedImageDataUrls = [];
      renderImagePreviews();
      const aiMessageIndex = aiChatApiOptionsBody.messages.length + messageOffset;
      const aiHistoryIndex = messagesHistory.length;
      let aiBubble = chat.addAIBubble(aiMessageIndex, aiHistoryIndex);
      aiBubble.updateStream('');
      const cancelButtonContainer = document.getElementById('cancel-button-container');
      const controller = new AbortController();
      const abortRequest = () => {
        cancelButtonContainer.style.display = 'none';
        controller.abort();
      };
      const cancelButton = cancelButtonContainer.querySelector('.cancel-button');
      cancelButton.addEventListener('click', abortRequest);
      const continueButton = cancelButtonContainer.querySelector('.continue-button');
      continueButton.style.display = 'none';
      cancelButtonContainer.style.display = 'flex';
      const onComplete = () => {
        isRequesting = false;
        sendButton.disabled = false;
        chat.chatBody.classList.remove('request-in-progress');
        cancelButton.removeEventListener('click', abortRequest);
        if (chat.chatController && !chat.chatController.userHasScrolled) {
          chat.chatController.scrollToBottom();
        }
        updateTokenUsage();
      };
      const onDone = createAIResponseHandler(aiBubble, messageOffset, aiMessageIndex, aiHistoryIndex, controller, onComplete);
      requestAiChat(aiBubble.updateStream.bind(aiBubble), onDone, controller.signal);
      messageInput.textContent = '';
    }
  }
  let mentionManager = null;
  if (messageInput) {
    mentionManager = new MentionManager(messageInput);
    mentionManager.onInsert = () => highlightMentions(messageInput);

    const mentionItemsMap = {
      Dir: (parentItem) => {
        return new Promise((resolve) => {
          initializeBackendConnection(async (backendObject) => {
            if (!backendObject) {
              resolve([]);
              return;
            }
            try {
              let targetPath;
              if (parentItem && parentItem.data && parentItem.data.path) {
                if (parentItem.data.path === '.') {
                  targetPath = JSON.parse(await backendObject.get_file_manager_cwd()).cwd;
                } else {
                  targetPath = parentItem.data.path;
                }
              } else {
                targetPath = JSON.parse(await backendObject.get_file_manager_cwd()).cwd;
              }
              const dirsData = await backendObject.listDirs(targetPath);
              const dirsResult = JSON.parse(dirsData);
              if (dirsResult.status === 'error') {
                console.error('获取目录列表失败:', dirsResult.content);
                resolve([]);
                return;
              }
              const list = [
                {
                  id: `dir00_${Date.now()}`,
                  icon: '📁',
                  label: `Dir:${targetPath}`,
                  hasChildren: false,
                  type: 'directory',
                },
              ];
              const dirs = dirsResult.dirs || [];
              for (let i = 0; i < dirs.length; i++) {
                list.push({
                  id: `dir${i}_${Date.now()}`,
                  icon: '📁',
                  label: `Dir:${targetPath}/${dirs[i]}`,
                  hasChildren: true,
                  type: 'directory',
                  data: { path: `${targetPath}/${dirs[i]}` },
                });
              }
              resolve(list);
            } catch (error) {
              console.error('获取目录列表异常:', error);
              resolve([]);
            }
          });
        });
      },
      File: () => {
        return new Promise((resolve) => {
          initializeBackendConnection(async (backendObject) => {
            if (!backendObject) {
              resolve([]);
              return;
            }
            const cwd = JSON.parse(await backendObject.get_file_manager_cwd()).cwd;
            const filesData = await backendObject.listFiles(cwd);
            const files = JSON.parse(filesData).files;
            const list = files.map((file, i) => ({
              id: `file${i}`,
              icon: '📄',
              label: `File:${cwd}/${file}`,
              hasChildren: false,
              type: 'file',
            }));
            resolve(list);
          });
        });
      },
      Terminal: () => {
        return new Promise((resolve) => {
          const terminalOptions = [];
          for (let i = 1; i <= 10; i++) {
            terminalOptions.push({
              id: `terminal${i}`,
              icon: '💻',
              label: `Terminal:${i}`,
              hasChildren: false,
              type: 'terminal',
            });
          }
          resolve(terminalOptions);
        });
      },
    };

    mentionManager.onGetSubItems = async function (item) {
      if (!this.ctrlPressed) {
        if (item.type === 'directory' && item.label.startsWith('Dir:')) {
          return null;
        }
      }
      if (mentionItemsMap[item.type]) {
        return await mentionItemsMap[item.type](item);
      }
      return null;
    };
    messageInput.addEventListener('paste', handlePaste);
    messageInput.addEventListener('copy', function (event) {
      const selection = window.getSelection();
      if (!selection.rangeCount) return;
      const range = selection.getRangeAt(0);
      const fragment = range.cloneContents();
      const plainText = fragment.textContent;
      event.preventDefault();
      event.clipboardData.setData('text/plain', plainText);
    });
    messageInput.addEventListener('cut', function (event) {
      const selection = window.getSelection();
      if (!selection.rangeCount) return;
      const range = selection.getRangeAt(0);
      const fragment = range.cloneContents();
      const plainText = fragment.textContent;
      event.preventDefault();
      event.clipboardData.setData('text/plain', plainText);
      range.deleteContents();
    });
    messageInput.addEventListener('input', function (event) {
      if (mentionManager.checkForMentionTrigger()) {
        const defaultItems = [
          { id: 'dir', icon: '📁', label: '目录', hasChildren: true, type: 'Dir', data: { path: '.' } },
          { id: 'file', icon: '📄', label: '文件', hasChildren: true, type: 'File', data: { path: '.' } },
          { id: 'url', icon: '🔗', label: '网址', hasChildren: false, type: 'Url', inputMode: true, placeholder: '请输入完整URL(如:https://example.com)' },
          { id: 'terminal', icon: '💻', label: '终端', hasChildren: true, type: 'Terminal' },
        ];
        mentionManager.show(defaultItems);
      } else if (mentionManager.isActive) {
        const text = messageInput.textContent;
        if (!text.includes('@')) {
          mentionManager.hide();
        }
      }
    });
    document.addEventListener('click', function (event) {
      if (mentionManager.isActive) {
        const popup = document.getElementById('mention-popup');
        if (!popup.contains(event.target)) {
          mentionManager.hide();
        }
      }
    });
    messageInput.addEventListener('keydown', function (event) {
      if (mentionManager.isActive) {
        mentionManager.ctrlPressed = event.ctrlKey;
        if (event.key === 'ArrowUp') {
          event.preventDefault();
          mentionManager.moveSelection('up');
          return;
        } else if (event.key === 'ArrowDown') {
          event.preventDefault();
          mentionManager.moveSelection('down');
          return;
        } else if (event.key === 'Enter') {
          event.preventDefault();
          mentionManager.selectItem();
          return;
        } else if (event.key === 'Escape') {
          event.preventDefault();
          mentionManager.hide();
          return;
        }
      }
      if (event.key === 'Enter' && !event.shiftKey && !event.ctrlKey) {
        event.preventDefault();
        sendMessage();
      }
    });
  }
  if (sendButton) {
    sendButton.addEventListener('click', sendMessage);
  }
  const imageButton = document.querySelector('#image-button');
  if (imageButton) {
    imageButton.addEventListener('click', () => {
      const fileInput = document.createElement('input');
      fileInput.type = 'file';
      fileInput.accept = 'image/*';
      fileInput.multiple = true;
      fileInput.addEventListener('change', (event) => {
        const files = event.target.files;
        if (files.length > 0) {
          Array.from(files).forEach((file) => {
            const reader = new FileReader();
            reader.onload = function (e) {
              pastedImageDataUrls.push(e.target.result);
              renderImagePreviews();
            };
            reader.readAsDataURL(file);
          });
        }
      });
      fileInput.click();
    });
  }
  const newChatButton = document.querySelector('.new-chat-button');
  if (newChatButton) {
    newChatButton.addEventListener('click', () => {
      window.location.reload();
    });
  }
  const settingsBtn = document.getElementById('settings-btn');
  const settingsPopup = document.getElementById('settings-popup');
  const closeSettingsBtn = document.getElementById('close-settings-btn');
  const settingsIframe = settingsPopup.querySelector('iframe');
  settingsIframe.addEventListener('load', () => {
    initializeBackendConnection((backendObject) => {
      if (backendObject) {
        const iframeWindow = settingsIframe.contentWindow;
        iframeWindow.backend = backendObject;
        if (iframeWindow.initializeWithBackend) {
          iframeWindow.initializeWithBackend(backendObject);
        }
      }
    });
  });
  settingsIframe.src = 'iframe/setting/index.html';
  settingsBtn.addEventListener('click', () => {
    settingsPopup.style.display = 'flex';
  });
  closeSettingsBtn.addEventListener('click', () => {
    const iframeWindow = settingsIframe.contentWindow;
    if (iframeWindow && typeof iframeWindow.getmodelsData === 'function') {
      const modelsData = iframeWindow.getmodelsData();
      if (backend) {
        backend.saveModels(JSON.stringify(modelsData));
        updateModelTags();
      }
    }
    settingsPopup.style.display = 'none';
  });
  window.addEventListener('click', (event) => {
    if (event.target === settingsPopup) {
      settingsPopup.style.display = 'none';
    }
  });
  const onlineStatusBtn = document.getElementById('online-status');
  const onlineUserPopup = document.getElementById('online-user-popup');
  const closeOnlineUserBtn = document.getElementById('close-online-user-btn');
  if (onlineStatusBtn && onlineUserPopup && closeOnlineUserBtn) {
    onlineStatusBtn.addEventListener('click', () => {
      onlineUserPopup.style.display = 'flex';
    });
    closeOnlineUserBtn.addEventListener('click', () => {
      onlineUserPopup.style.display = 'none';
    });
    window.addEventListener('click', (event) => {
      if (event.target === onlineUserPopup) {
        onlineUserPopup.style.display = 'none';
      }
    });
  }
  initializeBackendConnection((backend) => {
    initializeHistoryPanel(backend);
  });
  function updateAIBubbleMaxWidth() {
    const chatBody = document.querySelector('.chat-body');
    if (!chatBody) {
      return;
    }
    const maxWidth = chatBody.clientWidth;
    let styleTag = document.getElementById('dynamic-ai-bubble-style');
    if (!styleTag) {
      styleTag = document.createElement('style');
      styleTag.id = 'dynamic-ai-bubble-style';
      document.head.appendChild(styleTag);
    }
    styleTag.innerHTML = `
      .message-group.ai {
        max-width: ${maxWidth}px;
      }
      .message-content {
        box-sizing: border-box;
      }
    `;
  }
  updateAIBubbleMaxWidth();
  window.addEventListener('resize', updateAIBubbleMaxWidth);
  setupWebSocket();
});
function setupWebSocket() {
  const onlineStatusElement = document.getElementById('online-status');
  const statusIcon = onlineStatusElement.querySelector('.icon');
  const statusText = onlineStatusElement.querySelector('.status-text');
  const wsUrl = 'ws://aurashell-aichatapi.beefuny.shop/ws';
  let ws;
  let pingInterval;
  const onlineUserIframe = document.getElementById('online-user-iframe');
  const iframeWindow = onlineUserIframe ? onlineUserIframe.contentWindow : null;
  function connect() {
    ws = new WebSocket(wsUrl);
    window.ws = ws;
    ws.onopen = () => {
      statusIcon.classList.remove('error-icon');
      statusIcon.classList.add('success-icon');
      if (pingInterval) {
        clearInterval(pingInterval);
      }
      pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: 'ping', id: Date.now() }));
        }
      }, 30000);
      initializeBackendConnection(async (backendObject) => {
        if (backendObject) {
          let qqInfo = await backendObject.getQQUserInfo();
          setQQUserInfo(qqInfo.qq_name, qqInfo.qq_number);
        }
      });
    };
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.action === 'updateUserCount') {
          const data = JSON.parse(message.data);
          statusText.textContent = `在线用户数量:${data.userCount}`;
        }
        if (message.action === 'addUser') {
          const data = JSON.parse(message.data);
          let qq_number = data.qq_number.toString();
          if (qq_number == null || qq_number == '') {
            return;
          }
          if (window.OnlineUser[qq_number]) {
            return;
          }
          window.OnlineUser[qq_number] = data.qq_name;
          iframeWindow.addUser(qq_number, data.qq_name);
        }
        if (message.action === 'removeUser') {
          const data = JSON.parse(message.data);
          let qq_number = data.qq_number.toString();
          if (qq_number == null || qq_number == '') {
            return;
          }
          if (!window.OnlineUser[qq_number]) {
            return;
          }
          delete window.OnlineUser[data.qq_number.toString()];
          iframeWindow.removeUser(qq_number);
        }
        if (message.action === 'allUser') {
          try {
            const data = JSON.parse(message.data);
            if (data == null) {
              return;
            }
            window.OnlineUser = data;
            iframeWindow.allUser(data);
          } catch (e) {}
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };
    ws.onclose = () => {
      clearInterval(pingInterval);
      onlineStatusElement.title = '与在线状态服务器断开连接，正在尝试重新连接...';
      statusIcon.classList.remove('success-icon');
      statusIcon.classList.add('error-icon');
      statusText.textContent = '已断开';
      setTimeout(connect, 1000);
    };
    ws.onerror = (error) => {
      // console.error('WebSocket error:', error);
      ws.close();
    };
  }
  connect();
}
const modelSelectTrigger = document.getElementById('model-select-trigger');
const currentModelNameSpan = document.getElementById('current-model-name');
const modelSelectPopup = document.getElementById('model-select-popup');
const modelSearchInput = document.getElementById('model-search-input');
const modelOptionsContainer = document.getElementById('model-options-container');
let allModels = {};
window.currentModel = '';
function getCurrentModelData() {
  return allModels[window.currentModel];
}
async function updateModelTags() {
  if (!backend) {
    return;
  }
  const modelsDataString = await backend.getModels();
  allModels = JSON.parse(modelsDataString);
  const modelNames = Object.keys(allModels);
  if (modelNames.length > 0) {
    const savedModel = await backend.getSetting('ai_chat_model');
    if (savedModel && allModels.hasOwnProperty(savedModel)) {
      window.currentModel = savedModel;
    } else {
      window.currentModel = modelNames[0];
      backend.saveSetting('ai_chat_model', window.currentModel);
    }
  } else {
    window.currentModel = '';
  }
  currentModelNameSpan.textContent = window.currentModel;
  populateModelOptions();
}
function populateModelOptions(filter = '') {
  modelOptionsContainer.innerHTML = '';
  const lowerCaseFilter = filter.toLowerCase();
  Object.keys(allModels)
    .filter((modelName) => modelName.toLowerCase().includes(lowerCaseFilter))
    .forEach((modelName) => {
      const optionDiv = document.createElement('div');
      optionDiv.textContent = modelName;
      optionDiv.className = 'model-option';
      if (modelName === window.currentModel) {
        optionDiv.classList.add('active');
      }
      optionDiv.addEventListener('click', () => {
        window.currentModel = modelName;
        currentModelNameSpan.textContent = window.currentModel;
        modelSelectPopup.style.display = 'none';
        backend.saveSetting('ai_chat_model', window.currentModel);
        populateModelOptions();
      });
      modelOptionsContainer.appendChild(optionDiv);
    });
}
modelSelectTrigger.addEventListener('click', (e) => {
  e.stopPropagation();
  const isHidden = modelSelectPopup.style.display === 'none';
  modelSelectPopup.style.display = isHidden ? 'flex' : 'none';
  if (isHidden) {
    modelSearchInput.value = '';
    populateModelOptions();
    modelSearchInput.focus();
  }
});
modelSearchInput.addEventListener('input', () => {
  populateModelOptions(modelSearchInput.value);
});
document.addEventListener('click', (e) => {
  if (!modelSelectPopup.contains(e.target) && !modelSelectTrigger.contains(e.target)) {
    modelSelectPopup.style.display = 'none';
  }
});
function getAiChatApiOptionsBody() {
  aiChatApiOptionsBody.model = window.getCurrentModelData().model_name;
  return aiChatApiOptionsBody;
}
function getRequestAiChatApiOptions() {
  let key = getCurrentModelData().key;
  return {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${key}`,
      'User-Agent': 'RooCode/99999.99.9',
      Accept: 'application/json',
      'Accept-Encoding': 'br, gzip, deflate',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(getAiChatApiOptionsBody()),
  };
}
window.debugChatIndexes = {
  findByMessageIndex: function (index) {
    return document.querySelector(`[data-message-index="${index}"]`);
  },
  findByHistoryIndex: function (index) {
    return document.querySelector(`[data-history-index="${index}"]`);
  },
  showAllIndexes: function () {
    const elements = document.querySelectorAll('[data-message-index], [data-history-index]');
    const info = [];
    elements.forEach((elem) => {
      info.push({
        type: elem.classList.contains('user') ? 'user' : elem.classList.contains('ai') ? 'ai' : 'system',
        messageIndex: elem.dataset.messageIndex,
        historyIndex: elem.dataset.historyIndex,
        relatedIndex: elem.dataset.relatedMessageIndex,
        element: elem,
      });
    });
    console.table(info);
    return info;
  },
  validateIndexes: function () {
    const hasSystemMessage = aiChatApiOptionsBody.messages.length > 0 && aiChatApiOptionsBody.messages[0].role === 'system';
    const offset = hasSystemMessage ? 0 : 1;
    const issues = [];
    const elements = document.querySelectorAll('[data-message-index]');
    elements.forEach((elem) => {
      const domIndex = parseInt(elem.dataset.messageIndex);
      const actualIndex = domIndex - offset;
      if (actualIndex >= 0 && actualIndex < aiChatApiOptionsBody.messages.length) {
        const message = aiChatApiOptionsBody.messages[actualIndex];
        const expectedRole = elem.classList.contains('user') ? 'user' : 'assistant';
        if (message.role !== expectedRole) {
          issues.push({
            element: elem,
            domIndex,
            actualIndex,
            expectedRole,
            actualRole: message.role,
          });
        }
      } else {
        issues.push({
          element: elem,
          domIndex,
          actualIndex,
          error: 'Index out of bounds',
        });
      }
    });
    if (issues.length > 0) {
      console.error('Index validation issues:', issues);
    } else {
      console.log('All indexes are valid');
    }
    return issues;
  },
  showMessagesState: function () {
    console.log('System message exists:', aiChatApiOptionsBody.messages.length > 0 && aiChatApiOptionsBody.messages[0].role === 'system');
    console.log('Total messages:', aiChatApiOptionsBody.messages.length);
    console.log(
      'Messages:',
      aiChatApiOptionsBody.messages.map((m, i) => ({
        index: i,
        role: m.role,
        contentPreview: typeof m.content === 'string' ? m.content.substring(0, 50) + '...' : 'Complex content',
      })),
    );
  },
  showHistoryState: function () {
    console.log('Total history items:', messagesHistory.length);
    console.log(
      'History:',
      messagesHistory.map((item, i) => ({
        index: i,
        role: item.messages.role,
        isMcp: item.isMcp || false,
        contentPreview: typeof item.messages.content === 'string' ? item.messages.content.substring(0, 50) + '...' : 'Complex content',
      })),
    );
  },
};
async function requestAiChat(onStream, onDone, signal) {
  let fullContent = '';
  try {
    if (aiChatApiOptionsBody.messages.length === 0 || aiChatApiOptionsBody.messages[0].role !== 'system') {
      try {
        if (backend && typeof backend.getSystemPrompt === 'function') {
          const systemPrompt = await backend.getSystemPrompt();
          if (systemPrompt) {
            aiChatApiOptionsBody.messages.unshift({
              role: 'system',
              content: systemPrompt,
            });
          }
        } else {
          console.error('backend.getSystemPrompt is not available.');
        }
      } catch (err) {
        console.error('Error getting system prompt from backend:', err);
      }
    }
    let response;
    let retryCount = 0;
    const maxRetries = 5;
    while (true) {
      if (signal.aborted) {
        throw new DOMException('Request aborted by user', 'AbortError');
      }
      const options = getRequestAiChatApiOptions();
      options.signal = signal;
      response = await proxiedFetch(allModels[window.currentModel].api_url + '/chat/completions', options);
      if (response.status === 429) {
        if (retryCount >= maxRetries) {
          const errorMessage = `❌ **请求频率限制**\n\n服务器返回了 429 错误(请求过于频繁),已重试 ${maxRetries} 次后仍然失败。\n\n**建议:**\n- 请稍等片刻后再试\n- 或者切换到其他 API 模型`;
          if (onStream) {
            onStream(errorMessage);
          }
          if (onDone) {
            onDone(errorMessage);
          }
          return;
        }
        retryCount++;
        console.log(`Rate limit exceeded (429). Retrying after 1 second... (Attempt ${retryCount}/${maxRetries})`);
        await new Promise((resolve) => setTimeout(resolve, 1000));
        if (signal.aborted) {
          throw new DOMException('Request aborted by user', 'AbortError');
        }
        continue;
      }
      if (!response.ok) {
        const errorText = await response.text();
        try {
          const errorJson = JSON.parse(errorText);
          if (isContextLengthError(errorJson)) {
            if (retryCount >= maxRetries) {
              const errorMessage = `❌ **上下文长度超限**\n\n已尝试压缩上下文 ${maxRetries} 次，但仍然超出模型限制。\n\n**建议:**\n- 开启新对话\n- 或手动删除部分历史消息\n- 或切换到支持更长上下文的模型`;
              if (onStream) {
                onStream(errorMessage);
              }
              if (onDone) {
                onDone(errorMessage);
              }
              return;
            }
            let obj = await compressContext(aiChatApiOptionsBody, window.messagesHistory);
            if (obj) {
              aiChatApiOptionsBody = obj.aiChatApiOptionsBody;
              window.messagesHistory = obj.messagesHistory;
              retryCount++;
              continue;
            }
          }
        } catch (e) {}
      }
      break;
    }
    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `❌ **请求失败 (${response.status} ${response.statusText})**\n\n`;
      try {
        const errorJson = JSON.parse(errorText);
        if (errorJson.error && errorJson.error.message) {
          errorMessage += `**错误详情:**\n${errorJson.error.message}\n\n`;
          if (errorJson.error.type) {
            errorMessage += `**错误类型:** ${errorJson.error.type}\n`;
          }
          if (errorJson.error.code) {
            errorMessage += `**错误代码:** ${errorJson.error.code}\n`;
          }
        } else {
          errorMessage += errorText;
        }
      } catch (e) {
        errorMessage += errorText;
      }
      errorMessage += `\n**建议:** 请检查请求参数或稍后重试`;
      if (onStream) {
        onStream(errorMessage);
      }
      if (onDone) {
        onDone(errorMessage);
      }
      return;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        if (onDone) {
          onDone(fullContent);
        }
        return;
      }
      console.log('done', done, 'value', decoder.decode(value, { stream: true }));
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.substring(6).trim();
          try {
            const data = JSON.parse(dataStr);
            if (data.choices[0].finish_reason === 'stop') {
              if (onDone) {
                onDone(fullContent);
              }
              return;
            }
          } catch (e) {}
          if (dataStr === '[DONE]') {
            if (onDone) {
              onDone(fullContent);
            }
            return;
          }
          try {
            const data = JSON.parse(dataStr);
            if (data.choices && data.choices[0].delta && data.choices[0].delta.content) {
              const contentChunk = data.choices[0].delta.content;
              fullContent += contentChunk;
              if (onStream) {
                onStream(contentChunk);
              }
            }
          } catch (e) {}
        }
      }
    }
  } catch (error) {
    if (onDone) {
      onDone('Fetch Error:' + error);
    }
  }
}

async function proxiedFetch(url, options) {
  const proxySettingsStr = await backend.getSetting('ai_chat_proxy');
  try {
    const proxySettings = JSON.parse(proxySettingsStr);
    if (!proxySettings || !proxySettings.protocol || !proxySettings.host || !proxySettings.port) {
      return fetch(url, options);
    }
  } catch (e) {
    return fetch(url, options);
  }
  return new Promise((resolve, reject) => {
    const requestId = generateUniqueId();
    let streamController;
    const readableStream = new ReadableStream({
      start(controller) {
        streamController = controller;
      },
    });
    const onChunk = (receivedId, chunk) => {
      if (receivedId === requestId) {
        streamController.enqueue(new TextEncoder().encode(chunk));
      }
    };
    const onFinish = (receivedId, status, statusText, headersJson) => {
      if (receivedId === requestId) {
        cleanup();
        streamController.close();
        const headers = new Headers(JSON.parse(headersJson));
        const mockedResponse = {
          ok: status >= 200 && status < 300,
          status: status,
          statusText: statusText,
          headers: headers,
          body: readableStream,
          text: async () => {
            const reader = readableStream.getReader();
            let result = '';
            while (true) {
              const { done, value } = await reader.read();
              if (done) return result;
              result += new TextDecoder().decode(value);
            }
          },
          json: async () => {
            const text = await mockedResponse.text();
            return JSON.parse(text);
          },
        };
        resolve(mockedResponse);
      }
    };
    const onFail = (receivedId, errorMsg) => {
      if (receivedId === requestId) {
        cleanup();
        streamController.error(new Error(errorMsg));
        reject(new Error(errorMsg));
      }
    };
    const onAbort = () => {
      backend.cancelProxiedFetch(requestId);
      cleanup();
      reject(new DOMException('Request aborted by user', 'AbortError'));
    };
    const cleanup = () => {
      if (options.signal) {
        options.signal.removeEventListener('abort', onAbort);
      }
      backend.streamChunkReceived.disconnect(onChunk);
      backend.streamFinished.disconnect(onFinish);
      backend.streamFailed.disconnect(onFail);
    };
    if (options.signal) {
      options.signal.addEventListener('abort', onAbort, { once: true });
    }
    backend.streamChunkReceived.connect(onChunk);
    backend.streamFinished.connect(onFinish);
    backend.streamFailed.connect(onFail);
    const optionsForBackend = {
      method: options.method,
      headers: options.headers,
      body: options.body,
    };
    backend.proxiedFetch(requestId, url, JSON.stringify(optionsForBackend));
  });
}

let bodyStyle = '<style id="dynamic-body-style"></style>';
document.body.insertAdjacentHTML('beforeend', bodyStyle);
let bodyStyleElement = document.getElementById('dynamic-body-style');
let onresize = function () {
  bodyStyleElement.textContent = `
    .message-wrapper {
      max-width: calc(100% - 46px);
    }
  `;
};
window.addEventListener('resize', onresize);
onresize();
