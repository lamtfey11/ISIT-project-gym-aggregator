/**
 * Минимальные объявления типов njs (nginx JavaScript), которые использует компонент.
 * Полные типы — пакет njs-types из репозитория nginx/njs; здесь только нужное подмножество,
 * чтобы сборка не зависела от сети.
 */

interface NgxSharedDict {
  get(key: string): number | undefined;
  set(key: string, value: number, timeout?: number): NgxSharedDict;
  incr(key: string, delta: number, init?: number, timeout?: number): number;
  delete(key: string): boolean;
}

interface NgxObject {
  readonly shared: Record<string, NgxSharedDict | undefined>;
  log(level: number, message: string): void;
  readonly WARN: number;
}

interface NginxHTTPRequest {
  readonly method: string;
  readonly uri: string;
  readonly remoteAddress: string;
  readonly headersIn: Record<string, string | undefined>;
  readonly headersOut: Record<string, string | string[] | undefined>;
  return(status: number, body?: string): void;
  internalRedirect(uri: string): void;
}

declare const ngx: NgxObject;
