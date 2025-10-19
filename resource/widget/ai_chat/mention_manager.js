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
    if (!selection.rangeCount) {
      return;
    }
    const range = selection.getRangeAt(0);
    if (this.mentionStartNode) {
      const tempRange = document.createRange();
      tempRange.setStart(this.mentionStartNode, this.mentionStartOffset);
      tempRange.setEnd(range.startContainer, range.startOffset);
      tempRange.deleteContents();
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
}
