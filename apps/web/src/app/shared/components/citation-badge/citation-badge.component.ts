/**
 * CitationBadgeComponent — inline citation reference badge.
 * Clicking opens the source chunk in a tooltip/drawer.
 */
import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CitationEvent } from '../../../core/services/sse.service';

@Component({
  selector: 'cm-citation-badge',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span
      class="badge"
      [attr.data-type]="citation.source_type"
      [title]="tooltip"
      role="button"
      tabindex="0">
      <span class="type-icon">{{ icon }}</span>
      <span class="score">{{ scoreLabel }}</span>
    </span>
  `,
  styles: [`
    .badge {
      display: inline-flex; align-items: center; gap: 3px;
      padding: 2px 6px; border-radius: 4px; cursor: pointer;
      font-size: 11px; font-weight: 500;
      border: 0.5px solid var(--color-border-tertiary);
    }
    .badge[data-type="observation"]  { background: #E1F5EE; color: #0F6E56; }
    .badge[data-type="nursing_note"] { background: #E6F1FB; color: #185FA5; }
    .badge[data-type="protocol"]     { background: #EEEDFE; color: #3C3489; }
    .type-icon { font-size: 10px; }
    .score { opacity: 0.7; }
  `],
})
export class CitationBadgeComponent {
  @Input({ required: true }) citation!: CitationEvent;

  get icon(): string {
    return { observation: '📊', nursing_note: '📝', protocol: '📋' }[this.citation.source_type] ?? '📄';
  }

  get scoreLabel(): string {
    return (this.citation.score * 100).toFixed(0) + '%';
  }

  get tooltip(): string {
    return `Source: ${this.citation.source_type} | ${this.citation.timestamp ?? 'unknown time'} | Score: ${this.scoreLabel}`;
  }
}
