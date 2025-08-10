export const SCOPE_TABS = ['definition', 'lore', 'moment'];

export const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);
export const isArray = (value) => Array.isArray(value);