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
  addUserBubble(text, imageUrls) {
    const bubble = new UserBubble(this.chatBody);
    bubble.setContent(text, imageUrls);
    this.userHasScrolled = false;
    this.scrollToBottom();
    return bubble;
  }
  addAIBubble() {
    const bubble = new AIBubble(this.chatBody, this);
    return bubble;
  }
  addSystemBubble(toolName, code) {
    const bubble = new SystemBubble(this.chatBody);
    bubble.setToolCall(toolName, code);
    return bubble;
  }
}
class UserBubble {
  constructor(container) {
    const template = `<div class="message-group user">
              <div class="message-sender">
                <span class="icon">👤</span>
                <div>用户</div>
              </div>
              <div class="user-response"></div>
            </div>`;
    container.insertAdjacentHTML('beforeend', template);
    this.element = container.lastElementChild;
    this.contentElement = this.element.querySelector('.user-response');
  }
  setContent(text, imageUrls) {
    this.contentElement.innerHTML = '';
    if (text) {
      const textBlock = document.createElement('div');
      textBlock.style.whiteSpace = 'pre-wrap';
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
  constructor(container, chatController) {
    const template = `<div class="message-group ai">
              <div class="message-sender">
                <span class="icon">💬</span>
                <div>智能助手</div>
              </div>
              <div class="message-content"></div>
            </div>`;
    container.insertAdjacentHTML('beforeend', template);
    this.element = container.lastElementChild;
    this.contentElement = this.element.querySelector('.message-content');
    this.fullContent = '';
    this.isStreaming = false;
    this.chatController = chatController;
  }
  getHtml() {
    return this.contentElement.innerHTML;
  }
  setHTML(markdown) {
    this.isStreaming = false;
    this.fullContent = markdown;
    const dirtyHtml = marked.parse(markdown);
    const cleanHtml = DOMPurify.sanitize(dirtyHtml);
    this.contentElement.innerHTML = cleanHtml;
    if (this.chatController && !this.chatController.userHasScrolled) {
      this.chatController.scrollToBottom();
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
  constructor(container) {
    const template = `<div class="message-group system">
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
    this.toolNameElement = this.element.querySelector('.tool-name');
    this.detailElement = this.element.querySelector('.tool-call-body .code-block');
    this.resultContainer = this.element.querySelector('.tool-call-result');
    this.resultContentElement = this.element.querySelector('.tool-call-result .code-block');
    this.headerElement = this.element.querySelector('.tool-call-header');
    this.statusIconElement = this.element.querySelector('.tool-status-icon');
  }
  setToolCall(toolName, detail) {
    this.toolNameElement.textContent = toolName;
    this.detailElement.textContent = detail;
  }
  setResult(status, content) {
    this.statusIconElement.innerHTML = '';
    if (status === 'approved') {
      this.resultContentElement.textContent = content;
      this.statusIconElement.textContent = '▼';
      this.statusIconElement.classList.add('success');
      this.headerElement.addEventListener('click', () => {
        if (this.resultContentElement.textContent) {
          const isHidden = this.resultContainer.style.display === 'none';
          this.resultContainer.style.display = isHidden ? 'block' : 'none';
          this.statusIconElement.textContent = isHidden ? '▲' : '▼';
        }
      });
    } else if (status === 'rejected') {
      this.statusIconElement.textContent = '❌';
      this.resultContainer.style.display = 'none';
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
function handlePaste(event) {
  const items = (event.clipboardData || event.originalEvent.clipboardData).items;
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
  if (imageFound) {
    event.preventDefault();
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
window.loadHistory = function (filename) {
  initializeBackendConnection(async (backend) => {
    if (!backend) {
      return;
    }
    const history = await backend.loadHistory(filename);
    if (!history) {
      return;
    }
    window.firstUserMessage = filename.replace('.json', '');
    window.messagesHistory = history;
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
  marked.setOptions({
    highlight: function (code, lang) {
      const language = hljs.getLanguage(lang) ? lang : 'plaintext';
      return hljs.highlight(code, { language }).value;
    },
    langPrefix: 'hljs language-',
  });
  const chat = new ChatController('.chat-body');
  const chatHistoryContainer = document.querySelector('.chat-history');
  const textarea = document.querySelector('textarea[id="message-input"]');
  const sendButton = document.querySelector('.send-button');
  let isRequesting = false;
  let resizeTextarea = function () {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
  };
  function sendMessage() {
    if (isRequesting) {
      return;
    }
    const message = textarea.value.trim();
    if (message || pastedImageDataUrls.length > 0) {
      chatHistoryContainer.style.display = 'none';
      if (window.firstUserMessage === '') {
        window.firstUserMessage = message + '_' + Date.now().toString();
      }
      isRequesting = true;
      sendButton.disabled = true;
      chat.addUserBubble(message, [...pastedImageDataUrls]);
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
      const userMessage = {
        role: 'user',
        content: userMessageContent,
      };
      aiChatApiOptionsBody.messages.push(userMessage);
      messagesHistory.push({ messages: userMessage, isMcp: false });
      saveHistory(window.firstUserMessage, messagesHistory);
      pastedImageDataUrls = [];
      renderImagePreviews();
      let aiBubble = chat.addAIBubble();
      aiBubble.updateStream('');
      const cancelButtonContainer = document.getElementById('cancel-button-container');
      const controller = new AbortController();
      const abortRequest = () => controller.abort();
      const cancelButton = cancelButtonContainer.querySelector('.cancel-button');
      cancelButton.addEventListener('click', abortRequest);
      cancelButtonContainer.style.display = 'flex';
      const onDone = async (fullContent) => {
        aiBubble.finishStream();
        const assistantMessage = {
          role: 'assistant',
          content: fullContent,
        };
        aiChatApiOptionsBody.messages.push(assistantMessage);
        messagesHistory.push({ messages: assistantMessage, isMcp: false });
        saveHistory(window.firstUserMessage, messagesHistory);
        cancelButtonContainer.style.display = 'none';
        cancelButton.removeEventListener('click', abortRequest);
        isRequesting = false;
        sendButton.disabled = false;
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
                const systemBubble = chat.addSystemBubble(toolName, toolArgsStr);
                let userDecision = 'rejected';
                if (toolCall['auto_approve'] === true) {
                  userDecision = 'approved';
                } else {
                  userDecision = await systemBubble.requireApproval();
                }
                if (userDecision === 'approved') {
                  cancelButtonContainer.style.display = 'flex';
                  cancelButton.addEventListener('click', abortRequest);
                  isRequesting = true;
                  sendButton.disabled = true;
                  const executionResultStr = await backend.executeMcpTool(toolCall.server_name, toolCall.tool_name, JSON.stringify(toolCall.arguments));
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
                  aiBubble = chat.addAIBubble();
                  aiBubble.updateStream('');
                  requestAiChat(aiBubble.updateStream.bind(aiBubble), onDone, onError, controller.signal);
                } else {
                  systemBubble.setResult('rejected', 'User rejected the tool call.');
                }
              }
              if (this.chatController && !this.chatController.userHasScrolled) {
                this.chatController.scrollToBottom();
              }
            } catch (e) {
              console.error('Failed to process or execute MCP tool call:', e);
            }
          }
        }
      };
      const onError = (error) => {
        aiBubble.setHTML(`**Error:**\n\`\`\`\n${error.message}\n\`\`\``);
        cancelButtonContainer.style.display = 'none';
        cancelButton.removeEventListener('click', abortRequest);
        isRequesting = false;
        sendButton.disabled = false;
      };
      requestAiChat(aiBubble.updateStream.bind(aiBubble), onDone, onError, controller.signal);
      textarea.value = '';
      resizeTextarea();
    }
  }
  if (textarea) {
    textarea.addEventListener('paste', handlePaste);
    textarea.addEventListener('input', resizeTextarea);
    textarea.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' && !event.shiftKey && !event.ctrlKey) {
        event.preventDefault();
        sendMessage();
      }
    });
  }
  if (sendButton) {
    sendButton.addEventListener('click', sendMessage);
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
});
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
  aiChatApiOptionsBody.model = window.currentModel;
  return aiChatApiOptionsBody;
}
function getRequestAiChatApiOptions() {
  return {
    method: 'POST',
    headers: {
      'User-Agent': 'RooCode/99999.99.9',
      Accept: 'application/json',
      'Accept-Encoding': 'br, gzip, deflate',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(getAiChatApiOptionsBody()),
  };
}
async function requestAiChat(onStream, onDone, onError, signal) {
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
    while (true) {
      if (signal.aborted) {
        throw new DOMException('Request aborted by user', 'AbortError');
      }
      const options = getRequestAiChatApiOptions();
      options.signal = signal;
      response = await fetch(allModels[window.currentModel].api_url + '/chat/completions', options);
      if (response.status === 429) {
        console.log('Rate limit exceeded (429). Retrying after 1 second...');
        await new Promise((resolve) => setTimeout(resolve, 1000));
        if (signal.aborted) {
          throw new DOMException('Request aborted by user', 'AbortError');
        }
        continue;
      }
      break;
    }
    if (!response.ok) {
      const errorText = await response.text();
      const error = new Error(`${response.status} ${response.statusText}\n${errorText}`);
      if (onError) {
        onError(error);
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
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.substring(6).trim();
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
                console.log(`[${performance.now().toFixed(2)}] Received chunk:`, contentChunk);
              }
            }
          } catch (e) {
            // console.error('Error parsing JSON from stream:', dataStr, e);
          }
        }
      }
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('Request aborted by user.');
      if (onDone) {
        onDone(fullContent);
      }
    } else {
      console.error('Fetch error:', error);
      if (onError) onError(error);
    }
  }
}
