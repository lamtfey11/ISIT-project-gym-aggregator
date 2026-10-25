export interface RequestInfo {
  readonly method: string;
  readonly path: string;
  readonly clientIp: string;
  readonly authorization: string | null;
}

export interface LimitSpec {
  readonly limit: number;
  readonly periodSec: number;
  readonly burst?: number;
}

export interface LimitDecision {
  readonly allowed: boolean;
  readonly remaining: number;
  readonly retryAfterSec: number;
}

export type NextHop = "@user_api" | "@partner";

export interface GatewayDecision {
  readonly allowed: boolean;
  readonly policyName: string;
  readonly next: NextHop;
  readonly retryAfterSec: number;
  readonly headers: Readonly<Record<string, string>>;
}

export class RateLimitConfigError extends Error {}

export function validateSpec(spec: LimitSpec): LimitSpec {
  if (!Number.isInteger(spec.limit) || spec.limit < 1) {
    throw new RateLimitConfigError("limit должен быть целым числом ≥ 1");
  }
  if (spec.periodSec <= 0) {
    throw new RateLimitConfigError("periodSec должен быть > 0");
  }
  if (spec.burst !== undefined && spec.burst < 1) {
    throw new RateLimitConfigError("burst должен быть ≥ 1");
  }
  return spec;
}
