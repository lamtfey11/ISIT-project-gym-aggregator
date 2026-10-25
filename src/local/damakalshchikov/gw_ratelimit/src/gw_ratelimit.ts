import type { RequestInfo } from "./domain.js";
import { RateLimiter, rateLimitedBody } from "./limiter.js";
import { buildDefaultPolicies } from "./policies.js";
import { NjsSharedDictStore, SystemClock } from "./store.js";

const ZONE = "ratelimit";

let limiter: RateLimiter | null = null;

function getLimiter(): RateLimiter {
  if (limiter === null) {
    const dict = ngx.shared[ZONE];
    if (dict === undefined) {
      throw new Error(`Не объявлена зона js_shared_dict_zone ${ZONE}`);
    }
    limiter = new RateLimiter(buildDefaultPolicies(), new NjsSharedDictStore(dict), new SystemClock());
  }
  return limiter;
}

export function toRequestInfo(r: NginxHTTPRequest): RequestInfo {
  return {
    method: r.method,
    path: r.uri,
    clientIp: r.remoteAddress,
    authorization: r.headersIn["Authorization"] ?? null,
  };
}

function handle(r: NginxHTTPRequest): void {
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

export default { handle };
