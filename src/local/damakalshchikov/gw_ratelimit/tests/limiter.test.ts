import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { FixedWindowAlgorithm, SlidingWindowAlgorithm, TokenBucketAlgorithm } from "../src/algorithms.js";
import type { RateLimitAlgorithm } from "../src/algorithms.js";
import { RateLimitConfigError, validateSpec } from "../src/domain.js";
import type { LimitDecision, LimitSpec, RequestInfo } from "../src/domain.js";
import gw from "../src/gw_ratelimit.js";
import { BearerTokenKeyStrategy, IpKeyStrategy, fnv1a } from "../src/keys.js";
import { RateLimiter, rateLimitedBody } from "../src/limiter.js";
import { RoutePolicy, buildDefaultPolicies } from "../src/policies.js";
import { InMemoryCounterStore, ManualClock, NjsSharedDictStore } from "../src/store.js";

const START_MS = 1_700_000_000_000 - (1_700_000_000_000 % 60_000); // начало минутного окна

function req(over: Partial<RequestInfo> = {}): RequestInfo {
  return { method: "GET", path: "/api/v1/gyms", clientIp: "1.2.3.4", authorization: null, ...over };
}

function bearer(letter: string): string {
  return `Bearer ${letter.repeat(40)}`;
}

function setup(startMs: number = START_MS + 10_000) {
  const clock = new ManualClock(startMs);
  const store = new InMemoryCounterStore(clock);
  const limiter = new RateLimiter(buildDefaultPolicies(), store, clock);
  return { clock, store, limiter };
}

function countAllowed(limiter: RateLimiter, request: RequestInfo, times: number): number {
  let allowed = 0;
  for (let i = 0; i < times; i += 1) {
    if (limiter.check(request)?.allowed === true) {
      allowed += 1;
    }
  }
  return allowed;
}

describe("FixedWindowAlgorithm", () => {
  const spec: LimitSpec = { limit: 3, periodSec: 60 };

  it("пропускает limit запросов в окне и отклоняет остальные", () => {
    const clock = new ManualClock(START_MS + 10_000);
    const store = new InMemoryCounterStore(clock);
    const algorithm = new FixedWindowAlgorithm();
    const results = [1, 2, 3, 4].map(() => algorithm.check("k", spec, clock.nowMs(), store));
    assert.deepEqual(results.map((r) => r.allowed), [true, true, true, false]);
    assert.equal(results[0]?.remaining, 2);
    assert.equal(results[3]?.retryAfterSec, 50);
  });

  it("сбрасывает счётчик в новом окне", () => {
    const clock = new ManualClock(START_MS + 10_000);
    const store = new InMemoryCounterStore(clock);
    const algorithm = new FixedWindowAlgorithm();
    for (let i = 0; i < 4; i += 1) {
      algorithm.check("k", spec, clock.nowMs(), store);
    }
    clock.advance(60_000);
    assert.equal(algorithm.check("k", spec, clock.nowMs(), store).allowed, true);
  });
});

describe("SlidingWindowAlgorithm", () => {
  const spec: LimitSpec = { limit: 10, periodSec: 60 };

  it("пропускает не больше limit запросов в окне", () => {
    const clock = new ManualClock(START_MS + 10_000);
    const store = new InMemoryCounterStore(clock);
    const algorithm = new SlidingWindowAlgorithm();
    let allowed = 0;
    for (let i = 0; i < 15; i += 1) {
      if (algorithm.check("k", spec, clock.nowMs(), store).allowed) {
        allowed += 1;
      }
    }
    assert.equal(allowed, 10);
  });

  it("учитывает долю предыдущего окна и сглаживает стык окон", () => {
    const clock = new ManualClock(START_MS + 50_000);
    const store = new InMemoryCounterStore(clock);
    const algorithm = new SlidingWindowAlgorithm();
    for (let i = 0; i < 10; i += 1) {
      algorithm.check("k", spec, clock.nowMs(), store); // все 10 в конце окна
    }
    clock.advance(11_000); // 1 с нового окна: от предыдущего остаётся ~98 %
    assert.equal(algorithm.check("k", spec, clock.nowMs(), store).allowed, false);
    clock.advance(40_000); // 41 с нового окна: от предыдущего остаётся ~32 %
    assert.equal(algorithm.check("k", spec, clock.nowMs(), store).allowed, true);
  });

  it("не считает отклонённые запросы", () => {
    const clock = new ManualClock(START_MS + 10_000);
    const store = new InMemoryCounterStore(clock);
    const algorithm = new SlidingWindowAlgorithm();
    for (let i = 0; i < 30; i += 1) {
      algorithm.check("k", spec, clock.nowMs(), store);
    }
    assert.equal(store.get(`k:sw:${Math.floor(clock.nowMs() / 60_000)}`), 10);
  });
});

describe("TokenBucketAlgorithm", () => {
  const spec: LimitSpec = { limit: 60, periodSec: 60, burst: 30 };

  it("разрешает всплеск до burst, затем отклоняет", () => {
    const clock = new ManualClock(START_MS);
    const store = new InMemoryCounterStore(clock);
    const algorithm = new TokenBucketAlgorithm();
    let allowed = 0;
    for (let i = 0; i < 40; i += 1) {
      if (algorithm.check("k", spec, clock.nowMs(), store).allowed) {
        allowed += 1;
      }
    }
    assert.equal(allowed, 30);
  });

  it("пополняет корзину со скоростью limit за periodSec", () => {
    const clock = new ManualClock(START_MS);
    const store = new InMemoryCounterStore(clock);
    const algorithm = new TokenBucketAlgorithm();
    for (let i = 0; i < 30; i += 1) {
      algorithm.check("k", spec, clock.nowMs(), store);
    }
    clock.advance(5_000); // 5 токенов
    let allowed = 0;
    for (let i = 0; i < 10; i += 1) {
      if (algorithm.check("k", spec, clock.nowMs(), store).allowed) {
        allowed += 1;
      }
    }
    assert.equal(allowed, 5);
  });

  it("не копит токены больше ёмкости корзины", () => {
    const clock = new ManualClock(START_MS);
    const store = new InMemoryCounterStore(clock);
    const algorithm = new TokenBucketAlgorithm();
    algorithm.check("k", spec, clock.nowMs(), store);
    clock.advance(10 * 60_000);
    let allowed = 0;
    for (let i = 0; i < 40; i += 1) {
      if (algorithm.check("k", spec, clock.nowMs(), store).allowed) {
        allowed += 1;
      }
    }
    assert.equal(allowed, 30);
  });

  it("сообщает время до следующего токена", () => {
    const clock = new ManualClock(START_MS);
    const store = new InMemoryCounterStore(clock);
    const algorithm = new TokenBucketAlgorithm();
    let last: LimitDecision = { allowed: true, remaining: 0, retryAfterSec: 0 };
    for (let i = 0; i < 31; i += 1) {
      last = algorithm.check("k", spec, clock.nowMs(), store);
    }
    assert.equal(last.allowed, false);
    assert.equal(last.retryAfterSec, 1);
  });
});

describe("Стратегии ключа клиента", () => {
  it("IpKeyStrategy строит ключ по адресу", () => {
    assert.equal(new IpKeyStrategy().keyFor(req({ clientIp: "9.9.9.9" })), "ip:9.9.9.9");
  });

  it("BearerTokenKeyStrategy различает клиентов за одним адресом", () => {
    const strategy = new BearerTokenKeyStrategy();
    const a = strategy.keyFor(req({ authorization: bearer("a") }));
    const b = strategy.keyFor(req({ authorization: bearer("b") }));
    assert.notEqual(a, b);
    assert.match(a, /^tok:[0-9a-f]{8}$/);
  });

  it("не хранит токен в ключе", () => {
    const token = bearer("s");
    const key = new BearerTokenKeyStrategy().keyFor(req({ authorization: token }));
    assert.equal(key.includes("sss"), false);
    assert.equal(key, `tok:${fnv1a(token.slice(7))}`);
  });

  it("при отсутствии токена использует запасную стратегию", () => {
    const strategy = new BearerTokenKeyStrategy();
    assert.equal(strategy.keyFor(req({ authorization: null })), "ip:1.2.3.4");
    assert.equal(strategy.keyFor(req({ authorization: "Basic abcdefghijklmnopqrstuvwxyz" })), "ip:1.2.3.4");
    assert.equal(strategy.keyFor(req({ authorization: "Bearer short" })), "ip:1.2.3.4");
  });
});

describe("Проверка параметров лимита", () => {
  it("отклоняет неверные значения", () => {
    assert.throws(() => validateSpec({ limit: 0, periodSec: 60 }), RateLimitConfigError);
    assert.throws(() => validateSpec({ limit: 1.5, periodSec: 60 }), RateLimitConfigError);
    assert.throws(() => validateSpec({ limit: 10, periodSec: 0 }), RateLimitConfigError);
    assert.throws(() => validateSpec({ limit: 10, periodSec: 60, burst: 0 }), RateLimitConfigError);
  });

  it("RoutePolicy проверяет параметры при создании", () => {
    assert.throws(
      () => new RoutePolicy("bad", "/", null, new FixedWindowAlgorithm(), { limit: 0, periodSec: 1 }, new IpKeyStrategy(), "@user_api"),
      RateLimitConfigError,
    );
  });
});

describe("RoutePolicy.matches", () => {
  const policy = new RoutePolicy("p", "/webhooks/", ["POST"], new FixedWindowAlgorithm(), { limit: 1, periodSec: 1 }, new IpKeyStrategy(), "@partner");

  it("учитывает префикс пути и метод", () => {
    assert.equal(policy.matches(req({ method: "POST", path: "/webhooks/pay" })), true);
    assert.equal(policy.matches(req({ method: "GET", path: "/webhooks/pay" })), false);
    assert.equal(policy.matches(req({ method: "POST", path: "/api/x" })), false);
  });
});

describe("RateLimiter", () => {
  it("вход: 10 запросов в минуту с одного адреса", () => {
    const { limiter } = setup();
    assert.equal(countAllowed(limiter, req({ method: "POST", path: "/api/v1/auth/login" }), 15), 10);
  });

  it("API: 120 запросов в минуту на токен, клиенты за одним адресом не делят лимит", () => {
    const { limiter } = setup();
    assert.equal(countAllowed(limiter, req({ authorization: bearer("a") }), 200), 120);
    assert.equal(limiter.check(req({ authorization: bearer("b") }))?.allowed, true);
  });

  it("побеждает первая подходящая политика", () => {
    const { limiter } = setup();
    assert.equal(limiter.check(req({ method: "POST", path: "/api/v1/auth/login" }))?.policyName, "auth_login");
    assert.equal(limiter.check(req({ path: "/api/v1/access/scan", authorization: bearer("a") }))?.policyName, "access_marks");
    assert.equal(limiter.check(req({ path: "/api/v1/gyms" }))?.policyName, "user_api");
    assert.equal(limiter.check(req({ method: "GET", path: "/api/v1/auth/login" }))?.policyName, "user_api");
  });

  it("направляет внешние системы в @partner, пользователей в @user_api", () => {
    const { limiter } = setup();
    assert.equal(limiter.check(req({ method: "POST", path: "/webhooks/pay" }))?.next, "@partner");
    assert.equal(limiter.check(req({ path: "/bi/report" }))?.next, "@partner");
    assert.equal(limiter.check(req())?.next, "@user_api");
  });

  it("возвращает null, если политики нет", () => {
    const { limiter } = setup();
    assert.equal(limiter.check(req({ path: "/health" })), null);
  });

  it("добавляет заголовки RateLimit-*, а Retry-After только при отказе", () => {
    const { limiter } = setup();
    const login = req({ method: "POST", path: "/api/v1/auth/login" });
    const first = limiter.check(login);
    assert.equal(first?.headers["RateLimit-Limit"], "10");
    assert.equal(first?.headers["RateLimit-Remaining"], "9");
    assert.equal(first?.headers["RateLimit-Policy"], "10;w=60");
    assert.equal("Retry-After" in (first?.headers ?? {}), false);
    for (let i = 0; i < 9; i += 1) {
      limiter.check(login);
    }
    const denied = limiter.check(login);
    assert.equal(denied?.allowed, false);
    assert.equal(denied?.headers["Retry-After"], "50");
  });

  it("тело 429 соответствует контракту RateLimitedError", () => {
    const { limiter } = setup();
    const login = req({ method: "POST", path: "/api/v1/auth/login" });
    let denied = limiter.check(login);
    for (let i = 0; i < 10; i += 1) {
      denied = limiter.check(login);
    }
    assert.ok(denied);
    assert.deepEqual(rateLimitedBody(denied), { error: "rate_limited", retry_after: 50 });
  });
});

describe("Подмена стратегий (Strategy, OCP)", () => {
  it("useAlgorithm меняет алгоритм без изменения RateLimiter", () => {
    const { limiter } = setup();
    limiter.useAlgorithm("bi_read", new TokenBucketAlgorithm());
    assert.equal(countAllowed(limiter, req({ path: "/bi/report" }), 150), 120);
  });

  it("useKeyStrategy меняет способ различать клиентов", () => {
    const { limiter } = setup();
    limiter.useKeyStrategy("user_api", new IpKeyStrategy());
    countAllowed(limiter, req({ authorization: bearer("a") }), 130);
    assert.equal(limiter.check(req({ authorization: bearer("b") }))?.allowed, false); // лимит теперь общий для адреса
  });

  it("принимает новый алгоритм, написанный снаружи, без правки существующих классов", () => {
    class DenyAll implements RateLimitAlgorithm {
      readonly name = "deny_all";
      check(): LimitDecision {
        return { allowed: false, remaining: 0, retryAfterSec: 7 };
      }
    }
    const { limiter } = setup();
    limiter.useAlgorithm("user_api", new DenyAll());
    const decision = limiter.check(req());
    assert.equal(decision?.allowed, false);
    assert.equal(decision?.headers["Retry-After"], "7");
  });

  it("сообщает об ошибке для неизвестной политики", () => {
    const { limiter } = setup();
    assert.throws(() => limiter.useAlgorithm("нет_такой", new FixedWindowAlgorithm()), RateLimitConfigError);
    assert.throws(() => limiter.useKeyStrategy("нет_такой", new IpKeyStrategy()), RateLimitConfigError);
  });

  it("ключи разных алгоритмов не пересекаются после подмены", () => {
    const { limiter, store } = setup();
    limiter.check(req({ method: "POST", path: "/api/v1/auth/login" }));
    limiter.useAlgorithm("auth_login", new SlidingWindowAlgorithm());
    assert.equal(countAllowed(limiter, req({ method: "POST", path: "/api/v1/auth/login" }), 15), 10);
    assert.ok(store.get(`auth_login:ip:1.2.3.4:fw:${Math.floor((START_MS + 10_000) / 60_000)}`) !== undefined);
  });
});

/** Простая замена общей зоны njs. */
class FakeSharedDict {
  readonly values = new Map<string, number>();
  readonly calls: string[] = [];

  get(key: string): number | undefined {
    this.calls.push(`get:${key}`);
    return this.values.get(key);
  }

  set(key: string, value: number, timeout?: number): this {
    this.calls.push(`set:${key}:${String(timeout)}`);
    this.values.set(key, value);
    return this;
  }

  incr(key: string, delta: number, init?: number, timeout?: number): number {
    this.calls.push(`incr:${key}:${String(timeout)}`);
    const next = (this.values.get(key) ?? init ?? 0) + delta;
    this.values.set(key, next);
    return next;
  }

  delete(key: string): boolean {
    return this.values.delete(key);
  }
}

describe("NjsSharedDictStore", () => {
  it("передаёт операции в общую зону njs вместе с временем жизни", () => {
    const dict = new FakeSharedDict();
    const store = new NjsSharedDictStore(dict);
    assert.equal(store.incr("a", 1, 0, 60_000), 1);
    assert.equal(store.incr("a", 1, 0, 60_000), 2);
    store.set("b", 5, 1000);
    assert.equal(store.get("b"), 5);
    assert.deepEqual(dict.calls, ["incr:a:60000", "incr:a:60000", "set:b:1000", "get:b"]);
  });
});

describe("Точка входа njs (gw_ratelimit.handle)", () => {
  interface FakeRequest {
    method: string;
    uri: string;
    remoteAddress: string;
    headersIn: Record<string, string | undefined>;
    headersOut: Record<string, string | string[] | undefined>;
    returned: { status: number; body: string | undefined } | null;
    redirectedTo: string | null;
    return(status: number, body?: string): void;
    internalRedirect(uri: string): void;
  }

  function fakeRequest(method: string, uri: string): FakeRequest {
    const request: FakeRequest = {
      method,
      uri,
      remoteAddress: "7.7.7.7",
      headersIn: {},
      headersOut: {},
      returned: null,
      redirectedTo: null,
      return(status: number, body?: string): void {
        request.returned = { status, body };
      },
      internalRedirect(target: string): void {
        request.redirectedTo = target;
      },
    };
    return request;
  }

  it("пропускает запросы через internalRedirect, а при превышении отвечает 429 с телом контракта", () => {
    (globalThis as unknown as { ngx: unknown }).ngx = { shared: { ratelimit: new FakeSharedDict() } };

    let last = fakeRequest("POST", "/api/v1/auth/login");
    for (let i = 0; i < 10; i += 1) {
      last = fakeRequest("POST", "/api/v1/auth/login");
      gw.handle(last as unknown as NginxHTTPRequest);
      assert.equal(last.redirectedTo, "@user_api");
      assert.equal(last.returned, null);
    }
    last = fakeRequest("POST", "/api/v1/auth/login");
    gw.handle(last as unknown as NginxHTTPRequest);
    assert.equal(last.redirectedTo, null);
    assert.equal(last.returned?.status, 429);
    assert.equal(last.headersOut["Content-Type"], "application/json");
    assert.ok(last.headersOut["Retry-After"] !== undefined);
    const body = JSON.parse(last.returned?.body ?? "{}") as { error: string; retry_after: number };
    assert.equal(body.error, "rate_limited");
    assert.ok(body.retry_after >= 1);
  });

  it("запрос без политики уходит в @user_api без ограничений", () => {
    const request = fakeRequest("GET", "/health");
    gw.handle(request as unknown as NginxHTTPRequest);
    assert.equal(request.redirectedTo, "@user_api");
    assert.equal(request.returned, null);
  });
});
