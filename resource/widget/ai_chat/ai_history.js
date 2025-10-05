function initializeHistoryPanel(backend) {
  const chatHistoryContainer = document.querySelector('.chat-history');
  if (!chatHistoryContainer) {
    console.error('History container element not found.');
    return;
  }
  window.loadHistoryList = async function () {
    if (!backend) {
      return;
    }
    try {
      const historyFilesJson = await backend.listHistories();
      const historyItems = JSON.parse(historyFilesJson);
      chatHistoryContainer.innerHTML = '';
      historyItems.forEach((history) => {
        const filename = history.filename;
        const item = document.createElement('div');
        item.className = 'history-item';
        const info = document.createElement('div');
        info.className = 'history-item-info';
        const title = document.createElement('div');
        title.className = 'history-item-title';
        title.textContent = filename.replace('.json', '');
        info.appendChild(title);
        const timestamp = document.createElement('div');
        timestamp.className = 'history-item-timestamp';
        const date = new Date(history.createdAt);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        timestamp.textContent = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
        info.appendChild(timestamp);
        item.appendChild(info);
        const actions = document.createElement('div');
        actions.className = 'history-item-actions';
        const deleteBtn = document.createElement('button');
        deleteBtn.innerHTML = '&#128465;';
        deleteBtn.title = 'Delete';
        deleteBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const success = await backend.deleteHistory(filename);
          if (success) {
            window.loadHistoryList();
          }
        });
        actions.appendChild(deleteBtn);
        item.appendChild(actions);
        item.addEventListener('click', () => {
          console.log(`History item clicked: ${filename}`);
        });
        chatHistoryContainer.appendChild(item);
      });
    } catch (e) {
      console.error('Error loading history list:', e);
      chatHistoryContainer.innerHTML = '<div class="history-item">Failed to load history.</div>';
    }
  };
  window.loadHistoryList();
}
