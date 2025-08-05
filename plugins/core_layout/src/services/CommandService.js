// plugins/core_layout/src/services/CommandService.js

/**
 * 管理和执行由插件贡献的命令。
 */
export class CommandService {
    constructor() {
        this.commands = new Map();
        console.log('[CommandService] Initialized.');
    }

    registerMetadata(commandId, metadata, pluginId) {
        if (!this.commands.has(commandId)) {
            this.commands.set(commandId, { ...metadata, pluginId });
        } else {
            // 可以根据优先级决定是否覆盖元数据
            console.warn(`[CommandService] Metadata for command '${commandId}' is already registered.`);
        }
    }

    /**
     * 注册一个命令。
     * @param {string} commandId - 命令的唯一ID, e.g., "sandboxes.create_new"
     * @param {object} command - 命令对象，包含执行逻辑。
     * @param {string} pluginId - 提供此命令的插件ID。
     */
    register(commandId, command, pluginId) {
        if (this.commands.has(commandId)) {
            // 注意：这里没有实现基于优先级的覆盖，可以按需添加
            console.warn(`[CommandService] Command '${commandId}' is being re-registered by plugin '${pluginId}'.`);
        }
        this.commands.set(commandId, { ...command, pluginId });
        console.log(`[CommandService] Command '${commandId}' registered by plugin '${pluginId}'.`);
    }

    /**
     * 执行一个命令。
     * @param {string} commandId - 要执行的命令ID。
     * @param  {...any} args - 传递给命令执行函数的参数。
     */
    async execute(commandId, ...args) {
        const command = this.commands.get(commandId);
        if (command && typeof command.handler === 'function') {
            console.log(`[CommandService] Executing command '${commandId}'...`);
            try {
                return await Promise.resolve(command.handler(...args));
            } catch (e) {
                console.error(`[CommandService] Error executing command '${commandId}':`, e);
            }
        } else {
            console.error(`[CommandService] Command '${commandId}' not found or handler is not a function.`);
        }
    }

    registerHandler(commandId, handler) {
        const command = this.commands.get(commandId);
        if (command) {
            if (command.handler) {
                console.warn(`[CommandService] Handler for command '${commandId}' is being overridden.`);
            }
            command.handler = handler;
            console.log(`[CommandService] Handler for command '${commandId}' registered.`);
        } else {
            console.error(`[CommandService] Cannot register handler. Command '${commandId}' metadata not found. Make sure it's declared in a manifest.json.`);
        }
    }

    /**
     * 获取所有命令的列表（可用于命令面板UI）。
     * @returns {Array<{id: string, title: string, pluginId: string}>}
     */
    getCommands() {
        return Array.from(this.commands.entries()).map(([id, cmd]) => ({
            id: id,
            title: cmd.title, // 命令的显示名称
            pluginId: cmd.pluginId
        }));
    }
}