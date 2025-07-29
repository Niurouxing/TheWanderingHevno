// <project_root>/scripts/preload.js
const dotenv = require('dotenv');
const path = require('path');

// __dirname 在这里是 <project_root>/scripts
// 我们要找的 .env 文件在上一级目录
const envPath = path.resolve(__dirname, '..', '.env');

console.log(`[PRELOAD SCRIPT] Starting...`);
console.log(`[PRELOAD SCRIPT] Current working directory: ${process.cwd()}`);
console.log(`[PRELOAD SCRIPT] Attempting to load .env file from absolute path: ${envPath}`);

const result = dotenv.config({ path: envPath });

if (result.error) {
  console.error('[PRELOAD SCRIPT] FATAL: Error loading .env file:', result.error);
  // 如果 .env 找不到，直接退出，避免更神秘的错误
  process.exit(1); 
}

if (result.parsed) {
    console.log('[PRELOAD SCRIPT] .env file loaded successfully.');
    if (process.env.GEMINI_API_KEY) {
        console.log('[PRELOAD SCRIPT] ✅ GEMINI_API_KEY found in process.env.');
    } else {
        console.error('[PRELOAD SCRIPT] ❌ WARNING: .env file was loaded, but GEMINI_API_KEY is NOT defined inside it.');
    }
}