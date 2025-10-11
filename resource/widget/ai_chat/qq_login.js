/**
 * 等待指定 selector 的元素出现
 * @param {string} selector - 要等待的元素的选择器
 * @param {number} [timeout=5000] - 超时时间，单位毫秒。-1 表示无限等待，默认 5000 毫秒。
 * @param {Element} [baseElement=document] - 要在其中搜索元素的元素，默认是 document
 * @param {number} [count=1] - 等待元素出现的数量，默认 1 个
 * @returns {Promise<Element|Element[]|null>} - 返回找到的元素、元素数组或 null
 */
function waitForSelector(selector, timeout = 5000, baseElement = document, count = 1) {
  if (timeout == null) {
    timeout = 5000;
  }
  if (baseElement == null) {
    baseElement = document;
  }
  if (count == null || count <= 0) {
    count = 1;
  }
  return new Promise((resolve) => {
    const startTime = Date.now();
    const checkElements = () => {
      const elements = Array.from(baseElement.querySelectorAll(selector));
      if (elements.length >= count) {
        observer.disconnect();
        return resolve(count === 1 ? elements[0] : elements);
      }
      if (timeout !== -1 && Date.now() - startTime > timeout) {
        observer.disconnect();
        return resolve(count === 1 ? null : []);
      }
    };
    const observer = new MutationObserver(checkElements);
    const initialCheck = checkElements();
    if (initialCheck) {
      return;
    }
    observer.observe(baseElement, {
      childList: true,
      subtree: true,
    });
    if (timeout !== -1) {
      setTimeout(() => {
        observer.disconnect();
        resolve(count === 1 ? null : []);
      }, timeout);
    }
  });
}

async function main() {
  let qlogin_list = await waitForSelector('[id="qlogin_list"]');
  let uin = qlogin_list.querySelector('[uin]');
  if (!uin) {
    window.backend.setQQUserInfo('', '');
    return;
  }
  let qqName = uin.innerText;
  let qq = uin.getAttribute('uin');
  window.backend.setQQUserInfo(qqName, qq);
}

main();
