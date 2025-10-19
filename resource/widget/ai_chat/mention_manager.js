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
    this.mentionStartOffset = 0;
    this.savedCursorPos = null;
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
      this.savedCursorPos = this.inputElement.selectionStart;
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
    const textarea = this.inputElement;
    const cursorPos = textarea.selectionStart;
    const textBefore = textarea.value.substring(0, cursorPos);
    const textAfter = textarea.value.substring(cursorPos);
    const lastAtIndex = textBefore.lastIndexOf('@');
    if (lastAtIndex !== -1) {
      const mentionText = `@${item.label}`;
      const beforeAt = textBefore.substring(0, lastAtIndex);
      const needSpaceBefore = beforeAt.length === 0 || (beforeAt[beforeAt.length - 1] !== ' ' && beforeAt[beforeAt.length - 1] !== '\n');
      const spacePrefix = needSpaceBefore ? ' ' : '';
      const newValue = beforeAt + spacePrefix + mentionText + ' ' + textBefore.substring(cursorPos) + textAfter;
      textarea.value = newValue;
      const newCursorPos = beforeAt.length + spacePrefix.length + mentionText.length + 1;
      textarea.setSelectionRange(newCursorPos, newCursorPos);
      textarea.focus();
      if (this.onInsert) {
        this.onInsert();
      }
    }
  }
  checkForMentionTrigger() {
    const textarea = this.inputElement;
    const cursorPos = textarea.selectionStart;
    const textBefore = textarea.value.substring(0, cursorPos);
    const lastAtIndex = textBefore.lastIndexOf(this.mentionTriggerChar);
    if (lastAtIndex !== -1 && lastAtIndex === textBefore.length - 1) {
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
