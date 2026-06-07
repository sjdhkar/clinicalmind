import { computed, inject } from '@angular/core';
import { patchState, signalStore, withComputed, withMethods, withState } from '@ngrx/signals';
import { ApiService } from '../services/api.service';
import { SseService, CitationEvent, MetadataEvent } from '../services/sse.service';

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

export interface AppState {
  activePatientId: string | null;
  activeEncounterId: string | null;
  patients: PatientRiskCard[];
  messages: ChatMessage[];
  streaming: boolean;
  evalMetrics: EvalMetric[];
}

const initialState: AppState = {
  activePatientId: null,
  activeEncounterId: null,
  patients: [],
  messages: [],
  streaming: false,
  evalMetrics: [],
};

export const AppStore = signalStore(
  { providedIn: 'root' },
  withState(initialState),
  withComputed(store => ({
    activePatient: computed(() => store.patients().find(p => p.patientId === store.activePatientId()) ?? null),
    criticalPatients: computed(() => store.patients().filter(p => p.riskLevel === 'critical' || p.riskLevel === 'high')),
    latestMessage: computed(() => { const m = store.messages(); return m.length > 0 ? m[m.length - 1] : null; }),
    isStreaming: computed(() => store.streaming()),
  })),
  withMethods((store, sseService = inject(SseService)) => ({
    selectPatient(patientId: string, encounterId: string): void {
      patchState(store, { activePatientId: patientId, activeEncounterId: encounterId, messages: [] });
    },
    setPatients(patients: PatientRiskCard[]): void {
      patchState(store, { patients });
    },
    setEvalMetrics(metrics: EvalMetric[]): void {
      patchState(store, { evalMetrics: metrics });
    },
    sendQuery(query: string): void {
      const patientId = store.activePatientId();
      const encounterId = store.activeEncounterId();
      if (!patientId || !encounterId) return;
      const userMsgId = crypto.randomUUID();
      const assistantMsgId = crypto.randomUUID();
      patchState(store, state => ({
        messages: [
          ...state.messages,
          { id: userMsgId, role: 'user' as const, content: query, citations: [], streaming: false, timestamp: new Date() },
          { id: assistantMsgId, role: 'assistant' as const, content: '', citations: [], streaming: true, timestamp: new Date() },
        ],
        streaming: true,
      }));
      sseService.connect('/api/chat/stream', { query, patient_id: patientId, encounter_id: encounterId }).subscribe({
        next: event => {
          switch (event.type) {
            case 'token':
              patchState(store, state => ({ messages: state.messages.map(m => m.id === assistantMsgId ? { ...m, content: m.content + event.data } : m) }));
              break;
            case 'citation':
              patchState(store, state => ({ messages: state.messages.map(m => m.id === assistantMsgId ? { ...m, citations: [...m.citations, JSON.parse(event.data)] } : m) }));
              break;
            case 'metadata':
              patchState(store, state => ({ messages: state.messages.map(m => m.id === assistantMsgId ? { ...m, metadata: JSON.parse(event.data), streaming: false } : m) }));
              break;
            case 'done':
              patchState(store, { streaming: false });
              break;
            case 'error':
              patchState(store, state => ({ messages: state.messages.map(m => m.id === assistantMsgId ? { ...m, content: '⚠ An error occurred. Please try again.', streaming: false } : m), streaming: false }));
              break;
          }
        },
        error: () => patchState(store, { streaming: false }),
      });
    },
  }))
);
