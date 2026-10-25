/**
 * Состояние экрана «Режим сканирования» в стиле Redux: действия + чистый редьюсер.
 * Подключается в хранилище adm_state_store: configureStore({ reducer: { access: accessReducer } }).
 */

import type { Direction } from "../../../contracts/ts/contracts.js";
import type { MarkOutcome } from "./domain.js";

export interface AccessState {
  readonly mode: string;
  readonly direction: Direction;
  readonly deliveryPolicy: string;
  readonly submitting: boolean;
  readonly last: MarkOutcome | null;
  readonly journal: readonly MarkOutcome[];
  readonly pendingCount: number;
}

export type AccessAction =
  | { readonly type: "access/modeChanged"; readonly mode: string }
  | { readonly type: "access/directionChanged"; readonly direction: Direction }
  | { readonly type: "access/deliveryPolicyChanged"; readonly policy: string }
  | { readonly type: "access/markSubmitted" }
  | { readonly type: "access/markFinished"; readonly outcome: MarkOutcome }
  | { readonly type: "access/pendingChanged"; readonly count: number };

export const JOURNAL_SIZE = 20;

export const initialAccessState: AccessState = {
  mode: "scan",
  direction: "IN",
  deliveryPolicy: "queue_exits_offline",
  submitting: false,
  last: null,
  journal: [],
  pendingCount: 0,
};

export function accessReducer(state: AccessState = initialAccessState, action: AccessAction): AccessState {
  switch (action.type) {
    case "access/modeChanged":
      return { ...state, mode: action.mode };
    case "access/directionChanged":
      return { ...state, direction: action.direction };
    case "access/deliveryPolicyChanged":
      return { ...state, deliveryPolicy: action.policy };
    case "access/markSubmitted":
      return { ...state, submitting: true };
    case "access/markFinished":
      return {
        ...state,
        submitting: false,
        last: action.outcome,
        journal: [action.outcome, ...state.journal].slice(0, JOURNAL_SIZE),
      };
    case "access/pendingChanged":
      return { ...state, pendingCount: action.count };
  }
}

export type Dispatch = (action: AccessAction) => void;
