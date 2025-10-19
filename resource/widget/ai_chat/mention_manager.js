class MentionManager {
  constructor(inputElement) {
    this.inputElement = inputElement;
    this.popup = document.getElementById('mention-popup');
    this.items = [];
    this.selectedIndex = 0;
    this.isActive = false;
    this.mentionTriggerChar = '@';
    this.onGetSubItems = null;
    this.onInsert = null;
    this.breadcrumb = [];
    this.mentionStartNode = null;
    this.mentionStartOffset = 0;
    this.savedRange = null;
  }
  show(items) {
    this.items = items;
    this.selectedIndex = 0;
    this.isActive = true;
    this.renderPopup();
    this.popup.style.display = 'block';
  }
  hide() {
    this.isActive = false;
    this.popup.style.display = 'none';
    this.popup.innerHTML = '';
    this.breadcrumb = [];
  }
  renderPopup() {
    this.popup.innerHTML = '';
    this.items.forEach((item, index) => {
      const itemDiv = document.createElement('div');
      itemDiv.className = 'mention-item';
      if (index === this.selectedIndex) {
        itemDiv.classList.add('active');
      }
      const iconSpan = document.createElement('span');
      iconSpan.className = 'mention-icon';
      iconSpan.textContent = item.icon;
      const labelSpan = document.createElement('span');
      labelSpan.className = 'mention-label';
      labelSpan.textContent = item.label;
      itemDiv.appendChild(iconSpan);
      itemDiv.appendChild(labelSpan);
      itemDiv.addEventListener('click', () => {
        this.selectedIndex = index;
        this.selectItem();
      });
      this.popup.appendChild(itemDiv);
    });
  }

  updateSelection() {
    const allItems = this.popup.querySelectorAll('.mention-item');
    allItems.forEach((item, index) => {
      if (index === this.selectedIndex) {
        item.classList.add('active');
        item.scrollIntoView({ block: 'nearest' });
      } else {
        item.classList.remove('active');
      }
    });
  }
  moveSelection(direction) {
    if (direction === 'up') {
      this.selectedIndex = Math.max(0, this.selectedIndex - 1);
    } else if (direction === 'down') {
      this.selectedIndex = Math.min(this.items.length - 1, this.selectedIndex + 1);
    }
    this.updateSelection();
  }
  async selectItem() {
    const item = this.items[this.selectedIndex];
    if (item.inputMode) {
      const selection = window.getSelection();
      if (selection.rangeCount > 0) {
        this.savedRange = selection.getRangeAt(0).cloneRange();
      }
      this.showInputMode(item);
      return;
    }
    if (item.hasChildren && this.onGetSubItems) {
      const subItems = await this.onGetSubItems(item);
      if (subItems && subItems.length > 0) {
        this.breadcrumb.push(item);
        this.show(subItems);
        return;
      }
    }
    this.insertMentionTag(item);
    this.hide();
  }
  insertMentionTag(item) {
    const selection = window.getSelection();
    let range;
    if (this.savedRange) {
      range = this.savedRange;
      this.savedRange = null;
    } else if (selection.rangeCount > 0) {
      range = selection.getRangeAt(0);
    } else {
      return;
    }
    if (this.mentionStartNode) {
      const tempRange = document.createRange();
      tempRange.setStart(this.mentionStartNode, this.mentionStartOffset);
      tempRange.setEnd(range.startContainer, range.startOffset);
      tempRange.deleteContents();
      range = tempRange;
    }
    const mentionText = ` @${item.label} `;
    const textNode = document.createTextNode(mentionText);
    range.insertNode(textNode);
    range.setStartAfter(textNode);
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);
    this.inputElement.focus();
    if (this.onInsert) {
      this.onInsert();
    }
  }
  checkForMentionTrigger() {
    const selection = window.getSelection();
    if (!selection.rangeCount) {
      return false;
    }
    const range = selection.getRangeAt(0);
    const textNode = range.startContainer;
    if (textNode.nodeType !== Node.TEXT_NODE) {
      return false;
    }
    const textBeforeCursor = textNode.textContent.substring(0, range.startOffset);
    const lastAtIndex = textBeforeCursor.lastIndexOf(this.mentionTriggerChar);
    if (lastAtIndex !== -1 && lastAtIndex === textBeforeCursor.length - 1) {
      this.mentionStartNode = textNode;
      this.mentionStartOffset = lastAtIndex;
      return true;
    }
    return false;
  }
  showInputMode(item) {
    this.popup.innerHTML = '';
    const inputContainer = document.createElement('div');
    inputContainer.className = 'mention-input-container';
    const title = document.createElement('div');
    title.className = 'mention-input-title';
    title.textContent = `${item.icon} ${item.label}`;
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'mention-input-field';
    input.placeholder = item.placeholder || '请输入内容';
    input.autocomplete = 'off';
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'mention-input-buttons';
    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'mention-input-confirm';
    confirmBtn.textContent = '确认';
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'mention-input-cancel';
    cancelBtn.textContent = '取消';
    const errorMsg = document.createElement('div');
    errorMsg.className = 'mention-input-error';
    errorMsg.style.display = 'none';
    buttonContainer.appendChild(confirmBtn);
    buttonContainer.appendChild(cancelBtn);
    inputContainer.appendChild(title);
    inputContainer.appendChild(input);
    inputContainer.appendChild(errorMsg);
    inputContainer.appendChild(buttonContainer);
    this.popup.appendChild(inputContainer);
    setTimeout(() => input.focus(), 100);
    const handleConfirm = () => {
      const value = input.value.trim();
      if (!value) {
        errorMsg.textContent = '输入不能为空';
        errorMsg.style.display = 'block';
        return;
      }
      if (item.type === 'Url') {
        if (!value.startsWith('http://') && !value.startsWith('https://')) {
          errorMsg.textContent = 'URL必须以 http:// 或 https:// 开头';
          errorMsg.style.display = 'block';
          return;
        }
      }
      const tagItem = {
        ...item,
        label: `${item.type}:${value}`,
      };
      this.insertMentionTag(tagItem);
      this.hide();
    };
    const handleCancel = () => {
      this.hide();
    };
    confirmBtn.addEventListener('click', handleConfirm);
    cancelBtn.addEventListener('click', handleCancel);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleConfirm();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        handleCancel();
      }
    });
    input.addEventListener('input', () => {
      errorMsg.style.display = 'none';
    });
  }
}
