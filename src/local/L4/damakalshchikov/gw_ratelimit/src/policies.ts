/** Политики маршрутов: какой алгоритм, какой ключ и какой лимит для группы маршрутов. */

import { FixedWindowAlgorithm, SlidingWindowAlgorithm, TokenBucketAlgorithm } from "./algorithms.js";
import type { RateLimitAlgorithm } from "./algorithms.js";
import { validateSpec } from "./domain.js";
import type { LimitSpec, NextHop, RequestInfo } from "./domain.js";
import { BearerTokenKeyStrategy, IpKeyStrategy } from "./keys.js";
import type { ClientKeyStrategy } from "./keys.js";

export class RoutePolicy {
  constructor(
    readonly name: string,
    readonly pathPrefix: string,
    readonly methods: readonly string[] | null,
    public algorithm: RateLimitAlgorithm,
    readonly spec: LimitSpec,
    public keyStrategy: ClientKeyStrategy,
    readonly next: NextHop,
  ) {
    validateSpec(spec);
  }

  matches(request: RequestInfo): boolean {
    const methodOk = this.methods === null || this.methods.includes(request.method);
    return methodOk && request.path.startsWith(this.pathPrefix);
  }
}

/**
 * Политики по умолчанию. Порядок важен: первая подходящая политика выигрывает,
 * поэтому частные префиксы идут раньше общего /api/.
 */
export function buildDefaultPolicies(): RoutePolicy[] {
  const fixed = new FixedWindowAlgorithm();
  const sliding = new SlidingWindowAlgorithm();
  const bucket = new TokenBucketAlgorithm();
  const ip = new IpKeyStrategy();
  const token = new BearerTokenKeyStrategy(ip);
  return [
    new RoutePolicy("auth_login", "/api/v1/auth/login", ["POST"], fixed, { limit: 10, periodSec: 60 }, ip, "@user_api"),
    new RoutePolicy(
      "access_marks",
      "/api/v1/access/",
      null,
      bucket,
      { limit: 60, periodSec: 60, burst: 30 },
      token,
      "@user_api",
    ),
    new RoutePolicy("payment_webhooks", "/webhooks/", ["POST"], sliding, { limit: 600, periodSec: 60 }, ip, "@partner"),
    new RoutePolicy("bi_read", "/bi/", null, sliding, { limit: 120, periodSec: 60 }, ip, "@partner"),
    new RoutePolicy("user_api", "/api/", null, sliding, { limit: 120, periodSec: 60 }, token, "@user_api"),
  ];
}
