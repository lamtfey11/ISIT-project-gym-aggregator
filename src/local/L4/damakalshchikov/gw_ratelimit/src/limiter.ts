/** Контекст шаблона «Стратегия»: модуль ограничения нагрузки API-шлюза. */

import type { RateLimitAlgorithm } from "./algorithms.js";
import { RateLimitConfigError } from "./domain.js";
import type { GatewayDecision, RequestInfo } from "./domain.js";
import type { ClientKeyStrategy } from "./keys.js";
import type { RoutePolicy } from "./policies.js";
import type { Clock, CounterStore } from "./store.js";
import type { RateLimitedError } from "../../../contracts/ts/contracts.js";

export class RateLimiter {
  constructor(
    private readonly policies: RoutePolicy[],
    private readonly store: CounterStore,
    private readonly clock: Clock,
  ) {}

  /** null — маршрут не ограничивается (например, /health); шлюз передаёт запрос дальше без проверки. */
  check(request: RequestInfo): GatewayDecision | null {
    const policy = this.policies.find((p) => p.matches(request));
    if (policy === undefined) {
      return null;
    }
    const key = `${policy.name}:${policy.keyStrategy.keyFor(request)}`;
    const decision = policy.algorithm.check(key, policy.spec, this.clock.nowMs(), this.store);
    const headers: Record<string, string> = {
      "RateLimit-Limit": String(policy.spec.limit),
      "RateLimit-Remaining": String(decision.remaining),
      "RateLimit-Policy": `${policy.spec.limit};w=${policy.spec.periodSec}`,
    };
    if (!decision.allowed) {
      headers["Retry-After"] = String(decision.retryAfterSec);
    }
    return {
      allowed: decision.allowed,
      policyName: policy.name,
      next: policy.next,
      retryAfterSec: decision.retryAfterSec,
      headers,
    };
  }

  /** Динамическая подмена алгоритма для политики без перезапуска логики модуля. */
  useAlgorithm(policyName: string, algorithm: RateLimitAlgorithm): void {
    this.policy(policyName).algorithm = algorithm;
  }

  useKeyStrategy(policyName: string, keyStrategy: ClientKeyStrategy): void {
    this.policy(policyName).keyStrategy = keyStrategy;
  }

  private policy(name: string): RoutePolicy {
    const found = this.policies.find((p) => p.name === name);
    if (found === undefined) {
      throw new RateLimitConfigError(`Нет политики ${name}`);
    }
    return found;
  }
}

/** Тело ответа 429 по общему контракту (fitagg_contracts.RateLimitedError). */
export function rateLimitedBody(decision: GatewayDecision): RateLimitedError {
  return { error: "rate_limited", retry_after: Math.max(1, decision.retryAfterSec) };
}
