// SPDX-License-Identifier: Apache-2.0

import { z } from 'zod';

const rosbridgePublishSchema = z.object({
  op: z.literal('publish'),
  topic: z.string().min(1),
  msg: z.unknown(),
});

const rosbridgeServiceResponseSchema = z.object({
  op: z.literal('service_response'),
  service: z.string().min(1),
  values: z.unknown(),
  result: z.boolean(),
  id: z.string().optional(),
});

export const rosbridgeMessageSchema = z.discriminatedUnion('op', [
  rosbridgePublishSchema,
  rosbridgeServiceResponseSchema,
]);

export type ValidatedPublish = z.infer<typeof rosbridgePublishSchema>;
export type ValidatedServiceResponse = z.infer<typeof rosbridgeServiceResponseSchema>;
export type ValidatedMessage = z.infer<typeof rosbridgeMessageSchema>;
