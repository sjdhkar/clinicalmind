import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

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
  connect(url: string, body: unknown): Observable<SseEvent> {
    const fullUrl = environment.production ? `${environment.apiUrl}${url}` : url;

    return new Observable<SseEvent>(subscriber => {
      const controller = new AbortController();

      fetch(fullUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify(body),
        signal: controller.signal,
      })
        .then(async response => {
          if (!response.ok) { subscriber.error(new Error(`HTTP ${response.status}`)); return; }
          const reader = response.body?.getReader();
          if (!reader) { subscriber.error(new Error('No body')); return; }
          const decoder = new TextDecoder();
          let buffer = '';
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() ?? '';
            let evtType = 'message', evtData = '';
            for (const line of lines) {
              if (line.startsWith('event: ')) evtType = line.slice(7).trim();
              else if (line.startsWith('data: ')) evtData = line.slice(6).trim();
              else if (line === '') {
                if (evtData) {
                  subscriber.next({ type: evtType as SseEvent['type'], data: evtData });
                  if (evtType === 'done') { subscriber.complete(); return; }
                }
                evtType = 'message'; evtData = '';
              }
            }
          }
          subscriber.complete();
        })
        .catch(err => { if (err.name !== 'AbortError') subscriber.error(err); });

      return () => controller.abort();
    });
  }
}
