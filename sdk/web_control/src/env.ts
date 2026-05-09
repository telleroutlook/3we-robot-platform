// SPDX-License-Identifier: Apache-2.0

import { z } from 'zod';

const envSchema = z.object({
  VITE_ROSBRIDGE_URL: z
    .string()
    .url()
    .refine((url) => url.startsWith('ws://') || url.startsWith('wss://'), {
      message: 'VITE_ROSBRIDGE_URL must use ws:// or wss:// protocol',
    }),
});

export type Env = z.infer<typeof envSchema>;

export function validateEnv(overrides?: Partial<Record<string, string>>): Env {
  const defaults: Record<string, string> = {
    VITE_ROSBRIDGE_URL: 'ws://localhost:9090',
  };

  const fromVite: Record<string, string | undefined> =
    typeof import.meta !== 'undefined' &&
    (import.meta as unknown as { env?: Record<string, string> }).env
      ? (import.meta as unknown as { env: Record<string, string> }).env
      : {};

  const raw = {
    VITE_ROSBRIDGE_URL: overrides?.VITE_ROSBRIDGE_URL ?? fromVite.VITE_ROSBRIDGE_URL ?? defaults.VITE_ROSBRIDGE_URL,
  };

  const result = envSchema.safeParse(raw);

  if (!result.success) {
    const errors = result.error.issues
      .map((issue) => `  ${issue.path.join('.')}: ${issue.message}`)
      .join('\n');
    throw new Error(`Environment validation failed:\n${errors}`);
  }

  return result.data;
}
