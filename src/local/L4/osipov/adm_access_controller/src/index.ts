/** Компонент adm_access_controller контейнера admin_web (C4 L4). */

export { accessReducer, initialAccessState, JOURNAL_SIZE } from "./accessSlice.js";
export type { AccessAction, AccessState, Dispatch } from "./accessSlice.js";
export { AccessController } from "./controller.js";
export { OnlineOnlyDelivery, QueueExitsOfflineDelivery } from "./delivery.js";
export type { DeliveryPolicy, DeliveryResult } from "./delivery.js";
export { NetworkError, RateLimitedApiError, UnknownModeError } from "./domain.js";
export type { MarkInput, MarkOutcome, MarkStatus } from "./domain.js";
export { ManualMarkStrategy, normalizeScan, ScanMarkStrategy } from "./modes.js";
export type { MarkModeStrategy, RequestMeta } from "./modes.js";
export type { AccessApi, Clock, IdGenerator, PendingMarksStore } from "./ports.js";
