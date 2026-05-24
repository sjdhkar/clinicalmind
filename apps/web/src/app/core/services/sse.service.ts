/**
 * SseService — Server-Sent Events client for ClinicalMind streaming responses.
 *
 * The AI orchestrator streams clinical responses token-by-token via SSE.
 * This service wraps the native EventSource API in an Observable so Angular
 * components can subscribe with automatic cleanup on component destroy.
 *
 * Event types emitted by the server:
 *   start    — stream started, contains trace_id
 *   token    — single word/token for progressive rendering
 *   citation — a retrieved chunk reference
 *   metadata — final metadata (agents, model, cost)
 *   done     — stream complete
 *   error    — server-side error
 */

import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface SseEvent {
  type: 'start' | 'token' | 'citation' | 'metadata' | 'done' | 'error';
  data: string;
}

export interface CitationEvent {
  chunk_id: string;
  source_type: string;
  timestamp: string | null;
  score: number;
}

export interface MetadataEvent {
  agents_used: string[];
  model_used: string;
  prompt_version: string;
  insufficient_data: boolean;
  citation_count: number;
}

@Injectable({ providedIn: 'root' })
export class SseService {
  /**
   * Open an SSE connection and emit typed events as an Observable.
   * The connection closes automatically when the Observable is unsubscribed.
   */
  connect(url: string, body: unknown): Observable<SseEvent> {
    return new Observable<SseEvent>(subscriber => {
      // POST + SSE requires a fetch-based approach since EventSource only supports GET
      const controller = new AbortController();

      fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify(body),
        signal: controller.signal,
      })
        .then(async response => {
          if (!response.ok) {
            subscriber.error(new Error(`HTTP ${response.status}`));
            return;
          }

          const reader = response.body?.getReader();
          if (!reader) {
            subscriber.error(new Error('No response body'));
            return;
          }

          const decoder = new TextDecoder();
          let buffer = '';

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() ?? '';  // keep incomplete line in buffer

            let eventType = 'message';
            let eventData = '';

            for (const line of lines) {
              if (line.startsWith('event: ')) {
                eventType = line.slice(7).trim();
              } else if (line.startsWith('data: ')) {
                eventData = line.slice(6).trim();
              } else if (line === '') {
                // Empty line = end of SSE event
                if (eventData) {
                  subscriber.next({
                    type: eventType as SseEvent['type'],
                    data: eventData,
                  });
                  if (eventType === 'done') {
                    subscriber.complete();
                    return;
                  }
                }
                eventType = 'message';
                eventData = '';
              }
            }
          }
          subscriber.complete();
        })
        .catch(err => {
          if (err.name !== 'AbortError') {
            subscriber.error(err);
          }
        });

      // Teardown: abort the fetch when Observable is unsubscribed
      return () => controller.abort();
    });
  }
}
