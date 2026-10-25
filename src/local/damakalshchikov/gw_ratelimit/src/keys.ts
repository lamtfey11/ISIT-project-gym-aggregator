import type { RequestInfo } from "./domain.js";

export interface ClientKeyStrategy {
  readonly name: string;
  keyFor(request: RequestInfo): string;
}

export class IpKeyStrategy implements ClientKeyStrategy {
  readonly name = "ip";

  keyFor(request: RequestInfo): string {
    return `ip:${request.clientIp}`;
  }
}

export class BearerTokenKeyStrategy implements ClientKeyStrategy {
  readonly name = "bearer_token";

  constructor(private readonly fallback: ClientKeyStrategy = new IpKeyStrategy()) {}

  keyFor(request: RequestInfo): string {
    const header = request.authorization;
    if (header === null || !header.startsWith("Bearer ") || header.length < 20) {
      return this.fallback.keyFor(request);
    }
    return `tok:${fnv1a(header.slice(7))}`;
  }
}

export function fnv1a(text: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}
