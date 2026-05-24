/**
 * ClinicalMind Signal Store — NgRx Signals-based state management.
 *
 * Manages:
 *   - Active patient context (patient_id, encounter_id)
 *   - Chat session: messages, streaming state, citations
 *   - Ward dashboard: patient list with risk scores
 *   - Eval dashboard data
 */

import { computed, inject } from '@angular/core';
import {
  patchState,
  signalStore,
  withComputed,
  withMethods,
  withState,
} from '@ngrx/signals';
import { ApiService } from '../services/api.service';
import { SseService, CitationEvent, MetadataEvent } from '../services/sse.service';

// ── Domain types ──────────────────────────────────────────────────

export interface PatientRiskCard {
  patientId: string;
  patientName: string;
  wardBed: string;
  news2Score: number;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  lastUpdated: Date;
  anomalyDetected: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations: CitationEvent[];
  metadata?: MetadataEvent;
  streaming: boolean;
  timestamp: Date;
}

export interface EvalMetric {
  date: string;
  faithfulness: number;
  answerRelevancy: number;
  contextPrecision: number;
  hallucination_rate: number;
  p95LatencyMs: number;
  costPerQuery: number;
}

// ── State shape ───────────────────────────────────────────────────

export interface AppState {
  // Patient context
  activePatientId: string | null;
  activeEncounterId: string | null;

  // Ward dashboard
  patients: PatientRiskCard[];
  patientsLoading: boolean;

  // Chat
  messages: ChatMessage[];
  streaming: boolean;
  streamingMessageId: string | null;

  // Eval dashboard
  evalMetrics: EvalMetric[];
  evalLoading: boolean;
}

const initialState: AppState = {
  activePatientId: null,
  activeEncounterId: null,
  patients: [],
  patientsLoading: false,
  messages: [],
  streaming: false,
  streamingMessageId: null,
  evalMetrics: [],
  evalLoading: false,
};

// ── Store definition ──────────────────────────────────────────────

export const AppStore = signalStore(
  { providedIn: 'root' },

  withState(initialState),

  withComputed(store => ({
    activePatient: computed(() =>
      store.patients().find(p => p.patientId === store.activePatientId()) ?? null
    ),
    criticalPatients: computed(() =>
      store.patients().filter(p => p.riskLevel === 'critical' || p.riskLevel === 'high')
    ),
    latestMessage: computed(() => {
      const msgs = store.messages();
      return msgs.length > 0 ? msgs[msgs.length - 1] : null;
    }),
    isStreaming: computed(() => store.streaming()),
  })),

  withMethods((store, sseService = inject(SseService), api = inject(ApiService)) => ({

    selectPatient(patientId: string, encounterId: string): void {
      patchState(store, {
        activePatientId: patientId,
        activeEncounterId: encounterId,
        messages: [],
      });
    },

    /**
     * Send a clinical query and stream the response.
     * Appends user message immediately, then streams assistant response token by token.
     */
    sendQuery(query: string): void {
      const patientId = store.activePatientId();
      const encounterId = store.activeEncounterId();
      if (!patientId || !encounterId) return;

      // Append user message immediately
      const userMsgId = crypto.randomUUID();
      const assistantMsgId = crypto.randomUUID();

      patchState(store, state => ({
        messages: [
          ...state.messages,
          {
            id: userMsgId,
            role: 'user' as const,
            content: query,
            citations: [],
            streaming: false,
            timestamp: new Date(),
          },
          {
            id: assistantMsgId,
            role: 'assistant' as const,
            content: '',
            citations: [],
            streaming: true,
            timestamp: new Date(),
          },
        ],
        streaming: true,
        streamingMessageId: assistantMsgId,
      }));

      // Open SSE stream
      sseService
        .connect('/api/chat/stream', { query, patient_id: patientId, encounter_id: encounterId })
        .subscribe({
          next: event => {
            switch (event.type) {
              case 'token':
                // Append token to the streaming message
                patchState(store, state => ({
                  messages: state.messages.map(m =>
                    m.id === assistantMsgId
                      ? { ...m, content: m.content + event.data }
                      : m
                  ),
                }));
                break;

              case 'citation':
                const citation: CitationEvent = JSON.parse(event.data);
                patchState(store, state => ({
                  messages: state.messages.map(m =>
                    m.id === assistantMsgId
                      ? { ...m, citations: [...m.citations, citation] }
                      : m
                  ),
                }));
                break;

              case 'metadata':
                const metadata: MetadataEvent = JSON.parse(event.data);
                patchState(store, state => ({
                  messages: state.messages.map(m =>
                    m.id === assistantMsgId ? { ...m, metadata, streaming: false } : m
                  ),
                }));
                break;

              case 'done':
                patchState(store, { streaming: false, streamingMessageId: null });
                break;

              case 'error':
                patchState(store, state => ({
                  messages: state.messages.map(m =>
                    m.id === assistantMsgId
                      ? { ...m, content: '⚠ An error occurred. Please try again.', streaming: false }
                      : m
                  ),
                  streaming: false,
                  streamingMessageId: null,
                }));
                break;
            }
          },
          error: err => {
            console.error('SSE error:', err);
            patchState(store, { streaming: false, streamingMessageId: null });
          },
        });
    },

    updatePatientRisk(update: Partial<PatientRiskCard> & { patientId: string }): void {
      patchState(store, state => ({
        patients: state.patients.map(p =>
          p.patientId === update.patientId ? { ...p, ...update } : p
        ),
      }));
    },

    setPatients(patients: PatientRiskCard[]): void {
      patchState(store, { patients, patientsLoading: false });
    },

    setEvalMetrics(metrics: EvalMetric[]): void {
      patchState(store, { evalMetrics: metrics, evalLoading: false });
    },
  }))
);
