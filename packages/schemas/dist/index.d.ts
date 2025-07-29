import { z } from 'zod';
export declare const PingRequestSchema: z.ZodObject<{
    message: z.ZodString;
}, "strip", z.ZodTypeAny, {
    message: string;
}, {
    message: string;
}>;
export type PingRequest = z.infer<typeof PingRequestSchema>;
