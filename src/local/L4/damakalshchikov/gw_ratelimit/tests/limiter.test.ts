/** Тесты gw_ratelimit (пакет gw_ratelimit) (node:test). Запуск: npm test. */

import assert from "node:assert/strict";
import { beforeEach, describe, it } from "node:test";

import type { RateLimitAlgorithm } from "../src/algorithms.js";
import { FixedWindowAlgorithm, SlidingWindowAlgorithm, TokenBucketAlgorithm } from "../src/algorithms.js";
import type { LimitDecision, LimitSpec, RequestInfo } from "../src/domain.js";
import { RateLimitConfigError } from "../src/domain.js";
import { BearerTokenKeyStrategy, IpKeyStrategy } from "../src/keys.js";
import { RateLimiter, rateLimitedBody } from "../src/limiter.js";
import { buildDefaultPolicies, RoutePolicy } from "../src/policies.js";
import { InMemoryCounterStore, ManualClock } from "../src/store.js";

const T0 = Date.UTC(2026, 9, 24, 9, 0, 0);

function req(path: string, method = "GET", ip = "10.0.0.1", authorization: string | null = null): RequestInfo {
  return { method, path, clientIp: ip, authorization };
}

function hit(limiter: RateLimiter, request: RequestInfo, times: number): boolean[] {
  const result: boolean[] = [];
  for (let i = 0; i < times; i += 1) {
    result.push(limiter.check(request)?.allowed ?? true);
  }
  return result;
}

/** Новый алгоритм без изменения RateLimiter (проверка OCP). */
class DenyAllAlgorithm implements RateLimitAlgorithm {
  readonly name = "deny_all";

  check(_key: string, _spec: LimitSpec, _nowMs: number): LimitDecision {
    return { allowed: false, remaining: 0, retryAfterSec: 30 };
  }
}

describe("RateLimiter с политиками по умолчанию", () => {
  let clock: ManualClock;
  let limiter: RateLimiter;

  beforeEach(() => {
    clock = new ManualClock(T0);
    limiter = new RateLimiter(buildDefaultPolicies(), new InMemoryCounterStore(clock), clock);
  });

  it("вход: 10 попыток в минуту с одного IP, затем 429 с Retry-After", () => {
    const results = hit(limiter, req("/api/v1/auth/login", "POST"), 11);
    assert.deepEqual(results.filter((a) => a).length, 10);
    const denied = limiter.check(req("/api/v1/auth/login", "POST"));
    assert.ok(denied !== null && !denied.allowed);
    assert.equal(denied.policyName, "auth_login");
    assert.equal(denied.headers["Retry-After"], "60");
    assert.deepEqual(rateLimitedBody(denied), { error: "rate_limited", retry_after: 60 });
  });

  it("лимит входа сбрасывается в следующем окне", () => {
    hit(limiter, req("/api/v1/auth/login", "POST"), 12);
    clock.advance(60_000);
    assert.equal(limiter.check(req("/api/v1/auth/login", "POST"))?.allowed, true);
  });

  it("сканер администратора: всплеск до 30 сканов, затем 1 скан в секунду", () => {
    const admin = req("/api/v1/access/marks", "POST", "10.0.0.5", "Bearer admin-token-0123456789");
    assert.equal(hit(limiter, admin, 31).filter((a) => a).length, 30);
    clock.advance(1_000);
    assert.equal(limiter.check(admin)?.allowed, true);
    assert.equal(limiter.check(admin)?.allowed, false);
  });

  it("пользователи за одним NAT не делят лимит (ключ по токену)", () => {
    const a = req("/api/v1/gyms", "GET", "100.64.0.1", "Bearer user-a-token-000000000");
    const b = req("/api/v1/gyms", "GET", "100.64.0.1", "Bearer user-b-token-000000000");
    assert.equal(hit(limiter, a, 125).filter((x) => x).length, 120);
    assert.equal(limiter.check(b)?.allowed, true);
  });

  it("webhook платёжного шлюза идёт в модуль внешних систем", () => {
    const decision = limiter.check(req("/webhooks/payments", "POST", "185.71.76.1"));
    assert.equal(decision?.next, "@partner");
    assert.equal(decision?.headers["RateLimit-Limit"], "600");
  });

  it("маршрут без политики не ограничивается", () => {
    assert.equal(limiter.check(req("/health")), null);
  });

  it("подмена алгоритма во время работы", () => {
    limiter.useAlgorithm("user_api", new DenyAllAlgorithm());
    const decision = limiter.check(req("/api/v1/gyms"));
    assert.equal(decision?.allowed, false);
    assert.equal(decision?.retryAfterSec, 30);
  });

  it("подмена стратегии ключа: по IP пользователи за NAT делят лимит", () => {
    limiter.useKeyStrategy("user_api", new IpKeyStrategy());
    const a = req("/api/v1/gyms", "GET", "100.64.0.1", "Bearer user-a-token-000000000");
    const b = req("/api/v1/gyms", "GET", "100.64.0.1", "Bearer user-b-token-000000000");
    hit(limiter, a, 120);
    assert.equal(limiter.check(b)?.allowed, false);
  });

  it("неизвестная политика — ошибка конфигурации", () => {
    assert.throws(() => limiter.useAlgorithm("nope", new FixedWindowAlgorithm()), RateLimitConfigError);
  });
});

describe("Алгоритмы", () => {
  it("скользящее окно не пропускает 2×limit на стыке окон", () => {
    const clock = new ManualClock(T0 + 59_000);
    const store = new InMemoryCounterStore(clock);
    const algo = new SlidingWindowAlgorithm();
    const spec = { limit: 10, periodSec: 60 };
    let allowed = 0;
    for (let i = 0; i < 10; i += 1) allowed += algo.check("k", spec, clock.nowMs(), store).allowed ? 1 : 0;
    clock.advance(2_000);
    for (let i = 0; i < 10; i += 1) allowed += algo.check("k", spec, clock.nowMs(), store).allowed ? 1 : 0;
    assert.ok(allowed <= 11, `пропущено ${allowed}`);
  });

  it("фиксированное окно пропускает 2×limit на стыке (известный недостаток)", () => {
    const clock = new ManualClock(T0 + 59_000);
    const store = new InMemoryCounterStore(clock);
    const algo = new FixedWindowAlgorithm();
    const spec = { limit: 10, periodSec: 60 };
    let allowed = 0;
    for (let i = 0; i < 10; i += 1) allowed += algo.check("k", spec, clock.nowMs(), store).allowed ? 1 : 0;
    clock.advance(2_000);
    for (let i = 0; i < 10; i += 1) allowed += algo.check("k", spec, clock.nowMs(), store).allowed ? 1 : 0;
    assert.equal(allowed, 20);
  });

  it("маркерная корзина восстанавливается со скоростью limit/period", () => {
    const clock = new ManualClock(T0);
    const store = new InMemoryCounterStore(clock);
    const algo = new TokenBucketAlgorithm();
    const spec = { limit: 6, periodSec: 60, burst: 3 };
    for (let i = 0; i < 3; i += 1) assert.equal(algo.check("k", spec, clock.nowMs(), store).allowed, true);
    const denied = algo.check("k", spec, clock.nowMs(), store);
    assert.equal(denied.allowed, false);
    assert.equal(denied.retryAfterSec, 10);
    clock.advance(10_000);
    assert.equal(algo.check("k", spec, clock.nowMs(), store).allowed, true);
  });

  it("ключ по токену без заголовка откатывается на IP", () => {
    const key = new BearerTokenKeyStrategy();
    assert.equal(key.keyFor(req("/api/x", "GET", "1.2.3.4")), "ip:1.2.3.4");
    assert.match(key.keyFor(req("/api/x", "GET", "1.2.3.4", "Bearer abcdefghijklmnopqrstuvwxyz")), /^tok:[0-9a-f]{8}$/);
  });

  it("неверный лимит отклоняется при создании политики", () => {
    assert.throws(
      () => new RoutePolicy("bad", "/x", null, new FixedWindowAlgorithm(), { limit: 0, periodSec: 60 }, new IpKeyStrategy(), "@user_api"),
      RateLimitConfigError,
    );
  });
});
