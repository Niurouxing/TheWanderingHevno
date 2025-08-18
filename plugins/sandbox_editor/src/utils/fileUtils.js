/**
 * @fileoverview 提供了用于在浏览器中处理文件导入和导出的辅助函数。
 */

/**
 * 触发浏览器下载，将给定的JavaScript对象保存为JSON文件。
 * @param {object} data - 要转换为JSON并保存的JavaScript对象。
 * @param {string} filename - 建议的下载文件名 (例如, 'my-data.json')。
 */
export function exportAsJson(data, filename) {
  // 移除任何仅用于UI的内部key
  const cleanedData = JSON.parse(JSON.stringify(data, (key, value) => {
    if (key.startsWith('_internal_')) {
      return undefined; // 在序列化过程中移除这些键
    }
    return value;
  }));

  const jsonString = JSON.stringify(cleanedData, null, 2);
  const blob = new Blob([jsonString], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  
  URL.revokeObjectURL(url);
}

/**
 * 提示用户选择一个本地JSON文件，并将其内容解析为JavaScript对象。
 * @returns {Promise<{data: object, filename: string}>} 一个解析为包含文件内容和文件名的对象的Promise。
 * @throws {Error} 如果用户取消选择、文件读取失败或JSON解析失败。
 */
export function importFromJson() {
  return new Promise((resolve, reject) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,application/json';

    input.onchange = (event) => {
      const file = event.target.files[0];
      if (!file) {
        return reject(new Error('未选择文件。'));
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = JSON.parse(e.target.result);
          resolve({ data, filename: file.name });
        } catch (err) {
          reject(new Error(`JSON解析失败: ${err.message}`));
        }
      };
      reader.onerror = (e) => {
        reject(new Error(`文件读取失败: ${e.target.error.message}`));
      };
      reader.readAsText(file);
    };
    
    input.click();
  });
}
