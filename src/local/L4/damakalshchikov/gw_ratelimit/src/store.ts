/** Порт хранилища счётчиков. В шлюзе — общая для всех worker-процессов зона js_shared_dict_zone. */

export interface CounterStore {
  get(key: string): number | undefined;
  set(key: string, value: number, ttlMs: number): void;
  /** Атомарное увеличение; если ключа нет — создаётся со значением init и сроком ttlMs. */
  incr(key: string, delta: number, init: number, ttlMs: number): number;
}

export interface Clock {
  nowMs(): number;
}

export class SystemClock implements Clock {
  nowMs(): number {
    return Date.now();
  }
}

/** Адаптер к ngx.shared.<zone> (зона объявлена с type=number). */
export class NjsSharedDictStore implements CounterStore {
  constructor(private readonly dict: NgxSharedDict) {}

  get(key: string): number | undefined {
    return this.dict.get(key);
  }

  set(key: string, value: number, ttlMs: number): void {
    this.dict.set(key, value, ttlMs);
  }

  incr(key: string, delta: number, init: number, ttlMs: number): number {
    return this.dict.incr(key, delta, init, ttlMs);
  }
}

/** Хранилище в памяти для тестов; срок жизни ключей считается по тем же часам, что и у лимитера. */
export class InMemoryCounterStore implements CounterStore {
  private readonly values = new Map<string, { value: number; expiresAt: number }>();

  constructor(private readonly clock: Clock) {}

  get(key: string): number | undefined {
    const entry = this.values.get(key);
    if (entry === undefined || entry.expiresAt <= this.clock.nowMs()) {
      this.values.delete(key);
      return undefined;
    }
    return entry.value;
  }

  set(key: string, value: number, ttlMs: number): void {
    this.values.set(key, { value, expiresAt: this.clock.nowMs() + ttlMs });
  }

  incr(key: string, delta: number, init: number, ttlMs: number): number {
    const current = this.get(key);
    const next = (current ?? init) + delta;
    const expiresAt = current === undefined ? this.clock.nowMs() + ttlMs : this.values.get(key)!.expiresAt;
    this.values.set(key, { value: next, expiresAt });
    return next;
  }
}

export class ManualClock implements Clock {
  constructor(private current: number) {}

  nowMs(): number {
    return this.current;
  }

  advance(ms: number): void {
    this.current += ms;
  }
}
