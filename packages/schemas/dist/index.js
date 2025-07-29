// packages/schemas/src/index.ts
import { z } from 'zod';
// 在这里放入您设计的 GraphSchema, NodeSchema 等
export const PingRequestSchema = z.object({
    message: z.string(),
});
