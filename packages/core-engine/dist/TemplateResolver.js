/**
 * 解析模板字符串，如 "Hello, {{input.name}}!"
 * @param template 模板字符串
 * @param context 当前的执行上下文
 * @returns 解析后的值，可以是字符串，也可以是对象/数组等原始值
 */
export function resolveTemplate(template, context) {
    if (typeof template !== 'string') {
        return template; // 只处理字符串模板
    }
    // 检查是否是单一占位符，如 "{{nodeA.output}}"
    // 这种情况下，我们希望返回原始值类型，而不仅仅是字符串
    const singlePlaceholderMatch = template.match(/^\{\{\s*([\w.-]+)\s*\}\}$/);
    if (singlePlaceholderMatch) {
        const key = singlePlaceholderMatch[1].trim();
        const value = getValueFromContext(key, context);
        // 如果找到了值，直接返回，保留其原始类型
        if (value !== undefined) {
            return value;
        }
    }
    // 对于包含文本的模板，如 "My name is {{var.name}}."
    // 我们执行字符串替换
    const placeholderRegex = /\{\{\s*([\w.-]+)\s*\}\}/g;
    return template.replace(placeholderRegex, (match, key) => {
        const value = getValueFromContext(key.trim(), context);
        if (value === undefined || value === null) {
            return match; // 未找到值，保留占位符
        }
        // 如果值是对象或数组，将其字符串化
        if (typeof value === 'object') {
            return JSON.stringify(value);
        }
        return String(value);
    });
}
/**
 * 从上下文中根据 key (e.g., "nodeId.outputId" or "variables.varName") 获取值
 */
function getValueFromContext(key, context) {
    const parts = key.split('.');
    if (parts.length < 2)
        return undefined;
    const [source, ...rest] = parts;
    const id = rest.join('.');
    if (source === 'variables') {
        return context.variables?.[id];
    }
    // 假设源是节点ID
    return context.outputs?.[source]?.[id];
}
//# sourceMappingURL=TemplateResolver.js.map