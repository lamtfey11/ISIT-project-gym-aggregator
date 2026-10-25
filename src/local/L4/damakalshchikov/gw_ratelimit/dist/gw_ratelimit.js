// src/domain.ts
var RateLimitConfigError = class extends Error {
};
function validateSpec(spec) {
  if (!Number.isInteger(spec.limit) || spec.limit < 1) {
    throw new RateLimitConfigError("limit \u0434\u043E\u043B\u0436\u0435\u043D \u0431\u044B\u0442\u044C \u0446\u0435\u043B\u044B\u043C \u0447\u0438\u0441\u043B\u043E\u043C \u2265 1");
  }
  if (spec.periodSec <= 0) {
    throw new RateLimitConfigError("periodSec \u0434\u043E\u043B\u0436\u0435\u043D \u0431\u044B\u0442\u044C > 0");
  }
  if (spec.burst !== void 0 && spec.burst < 1) {
    throw new RateLimitConfigError("burst \u0434\u043E\u043B\u0436\u0435\u043D \u0431\u044B\u0442\u044C \u2265 1");
  }
  return spec;
}

// src/limiter.ts
var RateLimiter = class {
  constructor(policies, store, clock) {
    this.policies = policies;
    this.store = store;
    this.clock = clock;
  }
  /** null — маршрут не ограничивается (например, /health); шлюз передаёт запрос дальше без проверки. */
  check(request) {
    const policy = this.policies.find((p) => p.matches(request));
    if (policy === void 0) {
      return null;
    }
    const key = `${policy.name}:${policy.keyStrategy.keyFor(request)}`;
    const decision = policy.algorithm.check(key, policy.spec, this.clock.nowMs(), this.store);
    const headers = {
      "RateLimit-Limit": String(policy.spec.limit),
      "RateLimit-Remaining": String(decision.remaining),
      "RateLimit-Policy": `${policy.spec.limit};w=${policy.spec.periodSec}`
    };
    if (!decision.allowed) {
      headers["Retry-After"] = String(decision.retryAfterSec);
    }
    return {
      allowed: decision.allowed,
      policyName: policy.name,
      next: policy.next,
      retryAfterSec: decision.retryAfterSec,
      headers
    };
  }
  /** Динамическая подмена алгоритма для политики без перезапуска логики модуля. */
  useAlgorithm(policyName, algorithm) {
    this.policy(policyName).algorithm = algorithm;
  }
  useKeyStrategy(policyName, keyStrategy) {
    this.policy(policyName).keyStrategy = keyStrategy;
  }
  policy(name) {
    const found = this.policies.find((p) => p.name === name);
    if (found === void 0) {
      throw new RateLimitConfigError(`\u041D\u0435\u0442 \u043F\u043E\u043B\u0438\u0442\u0438\u043A\u0438 ${name}`);
    }
    return found;
  }
};
function rateLimitedBody(decision) {
  return { error: "rate_limited", retry_after: Math.max(1, decision.retryAfterSec) };
}

// src/algorithms.ts
var FixedWindowAlgorithm = class {
  constructor() {
    this.name = "fixed_window";
  }
  check(key, spec, nowMs, store) {
    const periodMs = spec.periodSec * 1e3;
    const window = Math.floor(nowMs / periodMs);
    const count = store.incr(`${key}:fw:${window}`, 1, 0, periodMs);
    const retryAfterSec = Math.ceil(((window + 1) * periodMs - nowMs) / 1e3);
    return {
      allowed: count <= spec.limit,
      remaining: Math.max(0, spec.limit - count),
      retryAfterSec: count <= spec.limit ? 0 : retryAfterSec
    };
  }
};
var SlidingWindowAlgorithm = class {
  constructor() {
    this.name = "sliding_window";
  }
  check(key, spec, nowMs, store) {
    const periodMs = spec.periodSec * 1e3;
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
};
var TokenBucketAlgorithm = class {
  constructor() {
    this.name = "token_bucket";
  }
  check(key, spec, nowMs, store) {
    const capacity = spec.burst ?? spec.limit;
    const ratePerMs = spec.limit / (spec.periodSec * 1e3);
    const ttlMs = Math.ceil(capacity / ratePerMs) + 1e3;
    const tokensKey = `${key}:tb:tokens`;
    const stampKey = `${key}:tb:ts`;
    const lastStamp = store.get(stampKey) ?? nowMs;
    const stored = store.get(tokensKey) ?? capacity;
    const tokens = Math.min(capacity, stored + (nowMs - lastStamp) * ratePerMs);
    if (tokens < 1) {
      store.set(tokensKey, tokens, ttlMs);
      store.set(stampKey, nowMs, ttlMs);
      return { allowed: false, remaining: 0, retryAfterSec: Math.max(1, Math.ceil((1 - tokens) / ratePerMs / 1e3)) };
    }
    store.set(tokensKey, tokens - 1, ttlMs);
    store.set(stampKey, nowMs, ttlMs);
    return { allowed: true, remaining: Math.floor(tokens - 1), retryAfterSec: 0 };
  }
};

// src/keys.ts
var IpKeyStrategy = class {
  constructor() {
    this.name = "ip";
  }
  keyFor(request) {
    return `ip:${request.clientIp}`;
  }
};
var BearerTokenKeyStrategy = class {
  constructor(fallback = new IpKeyStrategy()) {
    this.fallback = fallback;
    this.name = "bearer_token";
  }
  keyFor(request) {
    const header = request.authorization;
    if (header === null || !header.startsWith("Bearer ") || header.length < 20) {
      return this.fallback.keyFor(request);
    }
    return `tok:${fnv1a(header.slice(7))}`;
  }
};
function fnv1a(text) {
  let hash = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}

// src/policies.ts
var RoutePolicy = class {
  constructor(name, pathPrefix, methods, algorithm, spec, keyStrategy, next) {
    this.name = name;
    this.pathPrefix = pathPrefix;
    this.methods = methods;
    this.algorithm = algorithm;
    this.spec = spec;
    this.keyStrategy = keyStrategy;
    this.next = next;
    validateSpec(spec);
  }
  matches(request) {
    const methodOk = this.methods === null || this.methods.includes(request.method);
    return methodOk && request.path.startsWith(this.pathPrefix);
  }
};
function buildDefaultPolicies() {
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
      "@user_api"
    ),
    new RoutePolicy("payment_webhooks", "/webhooks/", ["POST"], sliding, { limit: 600, periodSec: 60 }, ip, "@partner"),
    new RoutePolicy("bi_read", "/bi/", null, sliding, { limit: 120, periodSec: 60 }, ip, "@partner"),
    new RoutePolicy("user_api", "/api/", null, sliding, { limit: 120, periodSec: 60 }, token, "@user_api")
  ];
}

// src/store.ts
var SystemClock = class {
  nowMs() {
    return Date.now();
  }
};
var NjsSharedDictStore = class {
  constructor(dict) {
    this.dict = dict;
  }
  get(key) {
    return this.dict.get(key);
  }
  set(key, value, ttlMs) {
    this.dict.set(key, value, ttlMs);
  }
  incr(key, delta, init, ttlMs) {
    return this.dict.incr(key, delta, init, ttlMs);
  }
};

// src/gw_ratelimit.ts
var ZONE = "ratelimit";
var limiter = null;
function getLimiter() {
  if (limiter === null) {
    const dict = ngx.shared[ZONE];
    if (dict === void 0) {
      throw new Error(`\u041D\u0435 \u043E\u0431\u044A\u044F\u0432\u043B\u0435\u043D\u0430 \u0437\u043E\u043D\u0430 js_shared_dict_zone ${ZONE}`);
    }
    limiter = new RateLimiter(buildDefaultPolicies(), new NjsSharedDictStore(dict), new SystemClock());
  }
  return limiter;
}
function toRequestInfo(r) {
  return {
    method: r.method,
    path: r.uri,
    clientIp: r.remoteAddress,
    authorization: r.headersIn["Authorization"] ?? null
  };
}
function handle(r) {
  const decision = getLimiter().check(toRequestInfo(r));
  if (decision === null) {
    r.internalRedirect("@user_api");
    return;
  }
  for (const [name, value] of Object.entries(decision.headers)) {
    r.headersOut[name] = value;
  }
  if (!decision.allowed) {
    r.headersOut["Content-Type"] = "application/json";
    r.return(429, JSON.stringify(rateLimitedBody(decision)));
    return;
  }
  r.internalRedirect(decision.next);
}
var gw_ratelimit_default = { handle };
export {
  gw_ratelimit_default as default,
  toRequestInfo
};
