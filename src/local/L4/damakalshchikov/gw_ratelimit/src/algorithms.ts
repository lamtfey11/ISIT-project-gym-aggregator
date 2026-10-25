/** Алгоритмы ограничения частоты (семейство стратегий № 1). */

import type { LimitDecision, LimitSpec } from "./domain.js";
import type { CounterStore } from "./store.js";

export interface RateLimitAlgorithm {
  readonly name: string;
  check(key: string, spec: LimitSpec, nowMs: number, store: CounterStore): LimitDecision;
}

/** Фиксированное окно: просто и дёшево, но на стыке окон пропускает до 2×limit. Для входа (анти-подбор пароля). */
export class FixedWindowAlgorithm implements RateLimitAlgorithm {
  readonly name = "fixed_window";

  check(key: string, spec: LimitSpec, nowMs: number, store: CounterStore): LimitDecision {
    const periodMs = spec.periodSec * 1000;
    const window = Math.floor(nowMs / periodMs);
    const count = store.incr(`${key}:fw:${window}`, 1, 0, periodMs);
    const retryAfterSec = Math.ceil(((window + 1) * periodMs - nowMs) / 1000);
    return {
      allowed: count <= spec.limit,
      remaining: Math.max(0, spec.limit - count),
      retryAfterSec: count <= spec.limit ? 0 : retryAfterSec,
    };
  }
}

/** Скользящее окно (взвешенная сумма текущего и прошлого окна): сглаживает стык окон. Основной для API. */
export class SlidingWindowAlgorithm implements RateLimitAlgorithm {
  readonly name = "sliding_window";

  check(key: string, spec: LimitSpec, nowMs: number, store: CounterStore): LimitDecision {
    const periodMs = spec.periodSec * 1000;
    const window = Math.floor(nowMs / periodMs);
    const elapsedShare = (nowMs - window * periodMs) / periodMs;
    const previous = store.get(`${key}:sw:${window - 1}`) ?? 0;
    const currentKey = `${key}:sw:${window}`;
    const current = store.get(currentKey) ?? 0;
    const estimated = previous * (1 - elapsedShare) + current;
    if (estimated + 1 > spec.limit) {
      const retryAfterSec = Math.max(1, Math.ceil((1 - elapsedShare) * spec.periodSec));
      return { allowed: false, remaining: 0, retryAfterSec };
    }
    store.incr(currentKey, 1, 0, 2 * periodMs);
    return { allowed: true, remaining: Math.max(0, Math.floor(spec.limit - estimated - 1)), retryAfterSec: 0 };
  }
}

/**
 * Маркерная корзина: средняя скорость limit/periodSec, но допускает всплеск до burst.
 * Для сканера администратора: в час пик к стойке подходит очередь, сканы идут подряд.
 * Чтение и запись корзины в shared dict не атомарны между worker-процессами — допустимая
 * погрешность в несколько запросов, зафиксирована в README.
 */
export class TokenBucketAlgorithm implements RateLimitAlgorithm {
  readonly name = "token_bucket";

  check(key: string, spec: LimitSpec, nowMs: number, store: CounterStore): LimitDecision {
    const capacity = spec.burst ?? spec.limit;
    const ratePerMs = spec.limit / (spec.periodSec * 1000);
    const ttlMs = Math.ceil(capacity / ratePerMs) + 1000;
    const tokensKey = `${key}:tb:tokens`;
    const stampKey = `${key}:tb:ts`;

    const lastStamp = store.get(stampKey) ?? nowMs;
    const stored = store.get(tokensKey) ?? capacity;
    const tokens = Math.min(capacity, stored + (nowMs - lastStamp) * ratePerMs);

    if (tokens < 1) {
      store.set(tokensKey, tokens, ttlMs);
      store.set(stampKey, nowMs, ttlMs);
      return { allowed: false, remaining: 0, retryAfterSec: Math.max(1, Math.ceil((1 - tokens) / ratePerMs / 1000)) };
    }
    store.set(tokensKey, tokens - 1, ttlMs);
    store.set(stampKey, nowMs, ttlMs);
    return { allowed: true, remaining: Math.floor(tokens - 1), retryAfterSec: 0 };
  }
}
