/**
 * ChatComponent — streaming clinical AI conversation panel.
 *
 * Features:
 * - Progressive token rendering with blinking cursor via StreamingTextDirective
 * - Citation badges appear inline as SSE citation events arrive
 * - Metadata footer shows agents used, model, prompt version
 * - Query suggestions for common clinical questions
 * - Keyboard shortcut: Enter to send, Shift+Enter for newline
 */
import {
  ChangeDetectionStrategy, Component, ElementRef,
  ViewChild, computed, inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AppStore, ChatMessage } from '../../core/state/app.store';
import { StreamingTextDirective } from '../../shared/directives/streaming-text.directive';
import { CitationBadgeComponent } from '../../shared/components/citation-badge/citation-badge.component';

@Component({
  selector: 'cm-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, StreamingTextDirective, CitationBadgeComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="chat-panel">

      <!-- Message list -->
      <div class="messages" #messageContainer>
        @if (messages().length === 0) {
          <div class="empty-state">
            <p class="empty-title">Ask a clinical question</p>
            <div class="suggestions">
              @for (suggestion of suggestions; track suggestion) {
                <button class="suggestion-chip" (click)="sendQuery(suggestion)">
                  {{ suggestion }}
                </button>
              }
            </div>
          </div>
        }

        @for (msg of messages(); track msg.id) {
          <div class="message" [class.user]="msg.role === 'user'" [class.assistant]="msg.role === 'assistant'">

            @if (msg.role === 'assistant') {
              <div class="avatar">AI</div>
            }

            <div class="bubble">
              <!-- Progressive text rendering with cursor -->
              <p
                [appStreamText]="msg.content"
                [isStreaming]="msg.streaming"
                class="message-text">
              </p>

              <!-- Citation badges -->
              @if (msg.citations.length > 0) {
                <div class="citations">
                  @for (citation of msg.citations; track citation.chunk_id) {
                    <cm-citation-badge [citation]="citation" />
                  }
                </div>
              }

              <!-- Metadata footer -->
              @if (msg.metadata && !msg.streaming) {
                <div class="message-meta">
                  <span class="model-badge">{{ msg.metadata.model_used }}</span>
                  <span class="agents">{{ msg.metadata.agents_used.join(' · ') }}</span>
                  @if (msg.metadata.insufficient_data) {
                    <span class="insufficient-data">⚠ Insufficient data</span>
                  }
                </div>
              }
            </div>

            @if (msg.role === 'user') {
              <div class="avatar user-avatar">You</div>
            }
          </div>
        }

        @if (isStreaming() && !latestMessage()?.streaming) {
          <div class="thinking">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
          </div>
        }
      </div>

      <!-- Input area -->
      <div class="input-area">
        <textarea
          [(ngModel)]="query"
          (keydown.enter)="onEnterKey($event)"
          placeholder="Ask a clinical question about this patient..."
          rows="2"
          [disabled]="isStreaming()"
          class="query-input">
        </textarea>
        <button
          (click)="sendQuery(query)"
          [disabled]="isStreaming() || !query.trim()"
          class="send-btn">
          {{ isStreaming() ? 'Thinking...' : 'Send' }}
        </button>
      </div>

    </div>
  `,
  styles: [`
    .chat-panel {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--color-background-primary);
    }
    .messages {
      flex: 1;
      overflow-y: auto;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .message {
      display: flex;
      gap: 0.75rem;
      align-items: flex-start;
    }
    .message.user { flex-direction: row-reverse; }
    .avatar {
      width: 32px; height: 32px;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-size: 11px; font-weight: 500;
      background: var(--color-background-info);
      color: var(--color-text-info);
      flex-shrink: 0;
    }
    .user-avatar { background: var(--color-background-secondary); color: var(--color-text-secondary); }
    .bubble {
      max-width: 70%;
      background: var(--color-background-secondary);
      border-radius: 12px;
      padding: 0.75rem 1rem;
    }
    .message.user .bubble { background: var(--color-background-info); }
    .message-text { margin: 0; font-size: 14px; line-height: 1.6; white-space: pre-wrap; }
    .citations { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
    .message-meta {
      display: flex; gap: 8px; margin-top: 8px;
      font-size: 11px; color: var(--color-text-tertiary);
    }
    .model-badge {
      background: var(--color-background-tertiary);
      padding: 1px 6px; border-radius: 4px;
    }
    .insufficient-data { color: var(--color-text-warning); }
    .empty-state { text-align: center; padding: 3rem 1rem; }
    .empty-title { font-size: 15px; color: var(--color-text-secondary); margin-bottom: 1rem; }
    .suggestions { display: flex; flex-direction: column; gap: 8px; max-width: 400px; margin: 0 auto; }
    .suggestion-chip {
      text-align: left; padding: 0.5rem 0.75rem;
      background: var(--color-background-secondary);
      border: 0.5px solid var(--color-border-tertiary);
      border-radius: 8px; cursor: pointer;
      font-size: 13px; color: var(--color-text-secondary);
    }
    .suggestion-chip:hover { border-color: var(--color-border-secondary); }
    .thinking { display: flex; gap: 4px; padding: 0.5rem 1rem; }
    .dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: var(--color-text-tertiary);
      animation: bounce 1.2s infinite;
    }
    .dot:nth-child(2) { animation-delay: 0.2s; }
    .dot:nth-child(3) { animation-delay: 0.4s; }
    .input-area {
      display: flex; gap: 8px; padding: 1rem;
      border-top: 0.5px solid var(--color-border-tertiary);
    }
    .query-input {
      flex: 1; resize: none;
      border: 0.5px solid var(--color-border-secondary);
      border-radius: 8px; padding: 0.5rem 0.75rem;
      font-size: 14px; background: var(--color-background-primary);
      color: var(--color-text-primary);
    }
    .query-input:focus { outline: none; border-color: var(--color-border-primary); }
    .send-btn {
      padding: 0 1rem;
      background: var(--color-background-info);
      color: var(--color-text-info);
      border: none; border-radius: 8px; cursor: pointer; font-size: 14px;
    }
    .send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
    @keyframes bounce {
      0%, 80%, 100% { transform: scale(0); }
      40% { transform: scale(1); }
    }
    @keyframes blink {
      0%, 100% { opacity: 1; } 50% { opacity: 0; }
    }
  `],
})
export class ChatComponent {
  @ViewChild('messageContainer') messageContainer!: ElementRef;

  protected readonly store = inject(AppStore);
  protected readonly messages = this.store.messages;
  protected readonly isStreaming = this.store.isStreaming;
  protected readonly latestMessage = this.store.latestMessage;

  query = '';

  readonly suggestions = [
    'What are the latest vital sign trends for this patient?',
    'Summarise the nursing notes from the last 24 hours',
    'What is the patient\'s deterioration risk?',
    'What does the NICE guideline recommend for this condition?',
  ];

  sendQuery(q: string): void {
    if (!q.trim() || this.isStreaming()) return;
    this.store.sendQuery(q.trim());
    this.query = '';
    setTimeout(() => this.scrollToBottom(), 50);
  }

  onEnterKey(event: KeyboardEvent): void {
    if (!event.shiftKey) {
      event.preventDefault();
      this.sendQuery(this.query);
    }
  }

  private scrollToBottom(): void {
    const el = this.messageContainer?.nativeElement;
    if (el) el.scrollTop = el.scrollHeight;
  }
}
