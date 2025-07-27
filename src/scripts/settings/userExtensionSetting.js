// src/scripts/settings/userExtensionSetting.js

import { USER } from '../../core/manager.js';
import { apiKeyManager } from '../../core/apiKeyManager.js';

/**
 * 验证导入的管线对象是否具有基本结构。
 * @param {any} data - 从JSON文件解析出的数据。
 * @returns {boolean} - 如果数据结构有效则返回true。
 */
function isValidPipeline(data) {
    if (!Array.isArray(data)) {
        toastr.error("Invalid pipeline: The file content is not an array.", "Import Error");
        return false;
    }
    if (data.length === 0) {
        toastr.warning("Imported pipeline is empty.", "Import Warning");
        return true; // 空管线是有效的
    }
    const firstModule = data[0];
    if (typeof firstModule !== 'object' || firstModule === null || !('id' in firstModule) || !('name' in firstModule) || !('promptSlots' in firstModule)) {
        toastr.error("Invalid pipeline: Modules are missing required properties (id, name, promptSlots).", "Import Error");
        return false;
    }
    return true;
}

/**
 * 【新增】处理管线导出逻辑。
 */
function handleExportPipeline() {
    try {
        const currentPipeline = USER.settings.pipeline;
        const jsonString = JSON.stringify(currentPipeline, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        
        // 创建一个临时的下载链接
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `hevno-pipeline-${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(a);
        a.click();
        
        // 清理
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        toastr.success("Pipeline exported successfully!", "Export Complete");
    } catch (error) {
        console.error("[Hevno] Failed to export pipeline:", error);
        toastr.error("An error occurred while exporting the pipeline.", "Export Error");
    }
}

/**
 * 【新增】处理文件选择和管线导入逻辑。
 * @param {Event} event - 文件输入框的change事件。
 */
function handleImportPipeline(event) {
    const file = event.target.files[0];
    if (!file) {
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const content = e.target.result;
            const importedPipeline = JSON.parse(content);

            if (isValidPipeline(importedPipeline)) {
                // 验证通过，保存到设置中
                // USER.settings的Proxy会自动调用saveSettingsDebounced()
                USER.settings.pipeline = importedPipeline;
                toastr.success("Pipeline imported and saved successfully!", "Import Complete");
            }
        } catch (error) {
            console.error("[Hevno] Failed to import pipeline:", error);
            toastr.error(`Failed to read or parse the pipeline file: ${error.message}`, "Import Error");
        } finally {
            // 重置文件输入框，以便可以再次选择同一个文件
            event.target.value = '';
        }
    };
    reader.onerror = () => {
        toastr.error("Failed to read the selected file.", "File Read Error");
    };

    reader.readAsText(file);
}

/**
 * 渲染设置界面的当前值
 */
export function renderSettings() {
    $('#Hevno_enabled_switch').prop('checked', USER.settings.isEnabled);
    $('#Hevno_demo_string_input').val(USER.settings.demoString);

    const keys = USER.settings.geminiApiKeys || [];
    $('#hevno_gemini_keys_textarea').val(keys.join('\n'));
}

/**
 * 绑定UI元素的事件监听
 */
function bindEvents() {
    // 原有事件
    $('#Hevno_enabled_switch').on('change', function() {
        USER.settings.isEnabled = $(this).is(':checked');
    });
    $('#Hevno_demo_string_input').on('input', function() {
        USER.settings.demoString = $(this).val();
    });

    // 【新增】为新按钮和文件输入框绑定事件
    $('#hevno_export_pipeline_btn').on('click', handleExportPipeline);
    
    // 点击“导入”按钮时，实际触发隐藏的文件输入框
    $('#hevno_import_pipeline_btn').on('click', () => {
        $('#hevno_pipeline_file_input').click();
    });

    // 当用户选择了文件后，处理文件内容
    $('#hevno_pipeline_file_input').on('change', handleImportPipeline);

        $('#hevno_gemini_keys_textarea').on('input', function() {
        const keysString = $(this).val();
        const keysArray = keysString.split('\n').map(k => k.trim()).filter(k => k);
        USER.settings.geminiApiKeys = keysArray;
        // 立即通知密钥管理器更新其密钥池
        apiKeyManager.loadKeys();
    });
}

/**
 * 加载设置的主函数
 */
export function loadSettings() {
    renderSettings();
    bindEvents();
    apiKeyManager.loadKeys();
    console.log("[Hevno] Settings UI loaded and pipeline management events bound.");
}