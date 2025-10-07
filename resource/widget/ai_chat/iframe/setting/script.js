const configFileSelect = document.getElementById('config-file');
const baseUrlInput = document.getElementById('base-url');
const apiKeyInput = document.getElementById('api-key');
const modelNameInput = document.getElementById('model-name-input');
const modelOptionsList = document.getElementById('model-options-list');
const refreshModelsBtn = document.getElementById('refresh-models-btn');
const addConfigBtn = document.getElementById('add-config-btn');
const editConfigBtn = document.getElementById('edit-config-btn');
const deleteConfigBtn = document.getElementById('delete-config-btn');
const proxyProtocolSelect = document.getElementById('proxy-protocol');
const proxyHostInput = document.getElementById('proxy-host');
const proxyPortInput = document.getElementById('proxy-port');
const proxyUsernameInput = document.getElementById('proxy-username');
const proxyPasswordInput = document.getElementById('proxy-password');
const modal = document.getElementById('custom-modal');
const modalTitle = document.getElementById('modal-title');
const modalText = document.getElementById('modal-text');
const modalInput = document.getElementById('modal-input');
const modalConfirmBtn = document.getElementById('modal-confirm-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');
let modelsData = {};
let settingsData = {};
window.getmodelsData = function () {
  return modelsData;
};
const updateFormFields = () => {
  const selectedModelName = configFileSelect.value;
  if (selectedModelName && modelsData[selectedModelName]) {
    const modelDetails = modelsData[selectedModelName];
    baseUrlInput.value = modelDetails.api_url || '';
    apiKeyInput.value = modelDetails.key || '';
    modelNameInput.value = modelDetails.model_name || '';
    fetchModels();
  }
};
const updateModelDataFromInputs = () => {
  const selectedModelName = configFileSelect.value;
  if (selectedModelName && modelsData[selectedModelName]) {
    modelsData[selectedModelName].api_url = baseUrlInput.value;
    modelsData[selectedModelName].key = apiKeyInput.value;
    modelsData[selectedModelName].model_name = modelNameInput.value;
  }
};
const updateProxyDataFromInputs = () => {
    if (!settingsData.proxy) {
        settingsData.proxy = {};
    }
    settingsData.proxy = {
        protocol: proxyProtocolSelect.value,
        host: proxyHostInput.value,
        port: proxyPortInput.value,
        username: proxyUsernameInput.value,
        password: proxyPasswordInput.value,
    };
    if (window.backend) {
        window.backend.saveSetting('ai_chat_proxy', JSON.stringify(settingsData.proxy));
    }
};
window.initializeWithBackend = async (backendObject) => {
  window.backend = backendObject;
  let backend = backendObject;
  modelsData = JSON.parse(await backend.getModels());
  try {
    const proxySettings = await backend.getSetting('ai_chat_proxy');
    if (proxySettings) {
        settingsData.proxy = JSON.parse(proxySettings);
        proxyProtocolSelect.value = settingsData.proxy.protocol || '';
        proxyHostInput.value = settingsData.proxy.host || '';
        proxyPortInput.value = settingsData.proxy.port || '';
        proxyUsernameInput.value = settingsData.proxy.username || '';
        proxyPasswordInput.value = settingsData.proxy.password || '';
    }
  } catch (e) {
    console.error("Could not load proxy settings", e);
  }
  configFileSelect.innerHTML = '';
  for (const modelName in modelsData) {
    if (Object.hasOwnProperty.call(modelsData, modelName)) {
      const option = document.createElement('option');
      option.value = modelName;
      option.textContent = modelName;
      configFileSelect.appendChild(option);
    }
  }
  baseUrlInput.addEventListener('input', updateModelDataFromInputs);
  apiKeyInput.addEventListener('input', updateModelDataFromInputs);
  modelNameInput.addEventListener('input', updateModelDataFromInputs);
  proxyProtocolSelect.addEventListener('change', updateProxyDataFromInputs);
  proxyHostInput.addEventListener('input', updateProxyDataFromInputs);
  proxyPortInput.addEventListener('input', updateProxyDataFromInputs);
  proxyUsernameInput.addEventListener('input', updateProxyDataFromInputs);
  proxyPasswordInput.addEventListener('input', updateProxyDataFromInputs);
  configFileSelect.addEventListener('change', updateFormFields);
  const currentModelName = parent.window.currentModel;
  if (currentModelName && configFileSelect.querySelector(`option[value="${currentModelName}"]`)) {
    configFileSelect.value = currentModelName;
  } else if (configFileSelect.options.length > 0) {
    configFileSelect.selectedIndex = 0;
  }
  updateFormFields();
};
let availableModels = [];
const populateModelOptions = (filter = '') => {
  modelOptionsList.innerHTML = '';
  const lowerCaseFilter = filter.toLowerCase();
  const customOption = document.createElement('div');
  customOption.textContent = `使用自定义模型: "${filter}"`;
  customOption.addEventListener('click', () => {
    modelNameInput.value = filter;
    modelOptionsList.style.display = 'none';
    updateModelDataFromInputs();
  });
  modelOptionsList.appendChild(customOption);
  availableModels
    .filter((model) => model.id.toLowerCase().includes(lowerCaseFilter))
    .forEach((model) => {
      const optionDiv = document.createElement('div');
      optionDiv.textContent = model.id;
      optionDiv.addEventListener('click', () => {
        modelNameInput.value = model.id;
        modelOptionsList.style.display = 'none';
        updateModelDataFromInputs();
      });
      modelOptionsList.appendChild(optionDiv);
    });
};
const fetchModels = async () => {
  const baseUrl = baseUrlInput.value;
  const apiKey = apiKeyInput.value;
  if (!baseUrl) {
    availableModels = [];
    populateModelOptions();
    return;
  }
  try {
    const response = await fetch(new URL(baseUrl + '/models'), {
      headers: {
        Authorization: `Bearer ${apiKey}`,
      },
    });
    if (response.ok) {
      const models = await response.json();
      availableModels = models.data || [];
    } else {
      console.error('Failed to fetch models:', response.statusText);
      availableModels = [];
    }
  } catch (error) {
    console.error('Error fetching models:', error);
    availableModels = [];
  }
  populateModelOptions();
};
modelNameInput.addEventListener('focus', () => {
  populateModelOptions();
  modelOptionsList.style.display = 'block';
});
modelNameInput.addEventListener('input', () => {
  populateModelOptions(modelNameInput.value);
  modelOptionsList.style.display = 'block';
});
document.addEventListener('click', (e) => {
  if (!e.target.closest('.custom-select-container')) {
    modelOptionsList.style.display = 'none';
  }
});
refreshModelsBtn.addEventListener('click', fetchModels);
let modalConfirmCallback = null;
const showModal = ({ title, text, showInput = false, inputValue = '' }, callback) => {
  modalTitle.textContent = title;
  modalText.textContent = text;
  modalInput.style.display = showInput ? 'block' : 'none';
  modalInput.value = inputValue;
  modal.style.display = 'flex';
  modalConfirmCallback = callback;
};
const hideModal = () => {
  modal.style.display = 'none';
  modalConfirmCallback = null;
};
modalConfirmBtn.addEventListener('click', () => {
  if (modalConfirmCallback) {
    modalConfirmCallback(modalInput.value);
  }
});
modalCancelBtn.addEventListener('click', hideModal);
addConfigBtn.addEventListener('click', () => {
  showModal(
    {
      title: '添加新配置',
      text: '请输入新配置的名称:',
      showInput: true,
    },
    (newConfigName) => {
      if (newConfigName && !modelsData[newConfigName]) {
        modelsData[newConfigName] = {
          api_url: '',
          key: '',
          model_name: '',
        };
        const option = document.createElement('option');
        option.value = newConfigName;
        option.textContent = newConfigName;
        configFileSelect.appendChild(option);
        configFileSelect.value = newConfigName;
        updateFormFields();
        hideModal();
      }
    },
  );
});
editConfigBtn.addEventListener('click', () => {
  const oldConfigName = configFileSelect.value;
  if (!oldConfigName) {
    return;
  }
  showModal(
    {
      title: '编辑配置名称',
      text: `请输入新的名称来替换 "${oldConfigName}":`,
      showInput: true,
      inputValue: oldConfigName,
    },
    (newConfigName) => {
      if (newConfigName && newConfigName !== oldConfigName && !modelsData[newConfigName]) {
        modelsData[newConfigName] = modelsData[oldConfigName];
        delete modelsData[oldConfigName];
        const selectedOption = configFileSelect.querySelector(`option[value="${oldConfigName}"]`);
        if (selectedOption) {
          selectedOption.value = newConfigName;
          selectedOption.textContent = newConfigName;
        }
        hideModal();
      }
    },
  );
});
deleteConfigBtn.addEventListener('click', () => {
  const configNameToDelete = configFileSelect.value;
  if (!configNameToDelete) {
    return;
  }
  showModal(
    {
      title: '删除配置',
      text: `您确定要删除 "${configNameToDelete}" 这个配置吗？此操作不可撤销。`,
    },
    () => {
      delete modelsData[configNameToDelete];
      const selectedOption = configFileSelect.querySelector(`option[value="${configNameToDelete}"]`);
      if (selectedOption) {
        selectedOption.remove();
      }
      if (configFileSelect.options.length > 0) {
        configFileSelect.selectedIndex = 0;
      }
      updateFormFields();
      hideModal();
    },
  );
});
document.addEventListener('DOMContentLoaded', () => {
  const tabs = document.querySelectorAll('.sidebar nav li');
  const tabContents = document.querySelectorAll('.tab-content');
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      tabs.forEach((t) => t.classList.remove('active'));
      tabContents.forEach((c) => c.classList.remove('active'));
      tab.classList.add('active');
      const tabName = tab.getAttribute('data-tab');
      document.getElementById(tabName).classList.add('active');
    });
  });
});
