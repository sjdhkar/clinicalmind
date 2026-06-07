import {
  ChangeDetectionStrategy, Component, ElementRef, ViewChild, inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AppStore } from '../../core/state/app.store';
import { StreamingTextDirective } from '../../shared/directives/streaming-text.directive';
import { CitationBadgeComponent } from '../../shared/components/citation-badge/citation-badge.component';

@Component({
  selector: 'cm-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, StreamingTextDirective, CitationBadgeComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  /* KEY FIX: host styles make this element behave as a flex column that fills parent */
  host: { style: 'display:flex; flex-direction:column; flex:1; min-height:0; overflow:hidden;' },
  styles: [`
    .msgs  { flex:1; min-height:0; overflow-y:auto; padding:20px; display:flex; flex-direction:column; gap:14px; background:#0f1117; }
    .inp   { flex-shrink:0; padding:14px 16px; background:#161b27; border-top:1px solid #2d3748; }
    .ubub  { margin-left:auto; max-width:72%; }
    .abub  { max-width:72%; }
    .ub    { background:#1d4ed8; border-radius:14px 14px 2px 14px; padding:10px 14px; }
    .ab    { background:#1e2433; border:1px solid #2d3748; border-radius:14px 14px 14px 2px; padding:10px 14px; }
    .av    { width:30px; height:30px; border-radius:50%; background:#1d4ed8; display:flex;
             align-items:center; justify-content:center; font-size:10px; font-weight:700;
             color:white; flex-shrink:0; }
    .mtext { margin:0; font-size:13px; line-height:1.65; white-space:pre-wrap; color:#e2e8f0; }
    .cits  { display:flex; flex-wrap:wrap; gap:4px; margin-top:8px; padding-top:8px;
             border-top:1px solid #2d3748; }
    .meta  { font-size:10px; color:#475569; display:flex; flex-wrap:wrap; gap:6px; margin-top:5px; }
    .chip  { background:#1e2433; border:1px solid #2d3748; border-radius:4px; padding:1px 6px; }
    .sugg  { background:#1e2433; border:1px solid #2d3748; border-radius:8px;
             padding:9px 14px; font-size:12px; color:#94a3b8; cursor:pointer;
             text-align:left; width:100%; transition:all .15s; }
    .sugg:hover { border-color:#3b82f6; color:#e2e8f0; }
    .dot   { width:6px; height:6px; border-radius:50%; background:#4b5563;
             display:inline-block; animation:bop 1.2s infinite; }
    .dot:nth-child(2){animation-delay:.15s}
    .dot:nth-child(3){animation-delay:.30s}
    .ta    { background:#0f1117!important; color:#e2e8f0!important;
             border:1px solid #334155!important; border-radius:10px!important; resize:none; }
    .ta:focus { border-color:#3b82f6!important; box-shadow:0 0 0 2px rgba(59,130,246,.2)!important; }
    .sbtn  { background:#1d4ed8; border:none; border-radius:10px;
             padding:9px 18px; color:white; font-size:14px; flex-shrink:0; }
    .sbtn:disabled { opacity:.45; cursor:not-allowed; }
    @keyframes bop{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}
    @keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
    .streaming-cursor { animation:blink 1s step-end infinite; color:#64748b; }
    .fade-in { animation:fi .18s ease-out; }
    @keyframes fi{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
  `],
  template: `
    <!-- Messages -->
    <div class="msgs" #mc>

      @if(messages().length===0){
        <div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:20px">
          <div class="text-center mb-2">
            <i class="bi bi-chat-square-dots" style="font-size:2.2rem;color:#2d3748"></i>
            <p class="mb-0 mt-2" style="font-size:13px;color:#64748b">Ask a clinical question</p>
          </div>
          <div style="display:flex;flex-direction:column;gap:8px;width:100%;max-width:400px">
            @for(s of sugg; track s){
              <button class="sugg" (click)="send(s)">
                <i class="bi bi-arrow-right-circle me-2" style="color:#3b82f6"></i>{{s}}
              </button>
            }
          </div>
        </div>
      }

      @for(m of messages(); track m.id){
        <div class="fade-in" [class]="m.role==='user' ? 'd-flex justify-content-end gap-2 align-items-end' : 'd-flex gap-2 align-items-end'">

          @if(m.role==='assistant'){<div class="av">AI</div>}

          <div [class]="m.role==='user' ? 'ubub' : 'abub'">
            <div [class]="m.role==='user' ? 'ub' : 'ab'">
              <p class="mtext" [appStreamText]="m.content" [isStreaming]="m.streaming"></p>

              @if(m.citations.length>0){
                <div class="cits">
                  <span style="font-size:10px;color:#475569;line-height:20px;margin-right:2px">Sources:</span>
                  @for(c of m.citations; track c.chunk_id){<cm-citation-badge [citation]="c" />}
                </div>
              }
            </div>
            @if(m.metadata && !m.streaming){
              <div class="meta">
                <span class="chip"><i class="bi bi-cpu me-1" style="color:#60a5fa"></i>{{m.metadata.model_used}}</span>
                @for(a of m.metadata.agents_used; track a){
                  <span class="chip">{{a.replace('_',' ')}}</span>
                }
                @if(m.metadata.insufficient_data){
                  <span style="color:#f59e0b"><i class="bi bi-exclamation-triangle me-1"></i>Insufficient data</span>
                }
              </div>
            }
          </div>

          @if(m.role==='user'){
            <div class="av" style="background:#334155"><i class="bi bi-person" style="font-size:13px"></i></div>
          }
        </div>
      }

      @if(isStreaming() && messages().length>0 && !messages()[messages().length-1].streaming){
        <div class="d-flex gap-2 align-items-end">
          <div class="av">AI</div>
          <div class="ab px-3 py-2">
            <span class="dot"></span><span class="dot mx-1"></span><span class="dot"></span>
          </div>
        </div>
      }
    </div>

    <!-- Input -->
    <div class="inp">
      <div class="d-flex gap-2 align-items-end">
        <textarea class="ta form-control"
                  [(ngModel)]="q"
                  (keydown.enter)="onEnter($event)"
                  placeholder="Ask a clinical question… (Enter to send)"
                  rows="2"
                  [disabled]="isStreaming()">
        </textarea>
        <button class="sbtn" (click)="send(q)" [disabled]="isStreaming()||!q.trim()">
          @if(isStreaming()){<span class="spinner-border" style="width:14px;height:14px"></span>}
          @else{<i class="bi bi-send-fill"></i>}
        </button>
      </div>
      <p class="mb-0 mt-1" style="font-size:10px;color:#475569">
        <i class="bi bi-shield-check me-1" style="color:#10b981"></i>Grounded in patient records · NLI-verified
      </p>
    </div>
  `,
})
export class ChatComponent {
  @ViewChild('mc') mc!: ElementRef;
  protected readonly store      = inject(AppStore);
  protected readonly messages   = this.store.messages;
  protected readonly isStreaming = this.store.isStreaming;
  q = '';

  readonly sugg = [
    "What are the latest vital sign trends?",
    "Summarise the nursing notes from today",
    "What is the patient's NEWS2 score and risk?",
    "What does the NICE guideline recommend?",
  ];

  send(query: string): void {
    if (!query.trim() || this.isStreaming()) return;
    this.store.sendQuery(query.trim());
    this.q = '';
    setTimeout(() => {
      const el = this.mc?.nativeElement as HTMLElement;
      if (el) el.scrollTop = el.scrollHeight;
    }, 60);
  }

  onEnter(e: Event): void {
    if (!(e as KeyboardEvent).shiftKey) { e.preventDefault(); this.send(this.q); }
  }
}
