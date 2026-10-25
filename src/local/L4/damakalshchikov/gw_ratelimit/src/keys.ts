/** Стратегии выбора ключа клиента (семейство стратегий № 2): «кого» ограничиваем. */

import type { RequestInfo } from "./domain.js";

export interface ClientKeyStrategy {
  readonly name: string;
  keyFor(request: RequestInfo): string;
}

/** По IP-адресу: для анонимных запросов и внешних систем. */
export class IpKeyStrategy implements ClientKeyStrategy {
  readonly name = "ip";

  keyFor(request: RequestInfo): string {
    return `ip:${request.clientIp}`;
  }
}

/**
 * По токену доступа: пользователи за одним NAT (Wi-Fi зала, мобильный оператор) не делят лимит.
 * JWT на этой фазе ещё не проверен, поэтому берётся не содержимое, а хэш строки токена;
 * без токена — откат на IP.
 */
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

/** FNV-1a 32 бит: короткий ключ для shared dict, без зависимости от модуля crypto. */
export function fnv1a(text: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}
