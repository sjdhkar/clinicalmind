import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CitationEvent } from '../../../core/services/sse.service';

@Component({
  selector: 'cm-citation-badge',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span class="citation-badge"
          [class]="badgeClass"
          [title]="tooltip"
          role="button"
          tabindex="0">
      <i [class]="'bi ' + icon + ' me-1'" style="font-size:9px"></i>{{ scoreLabel }}
    </span>
  `,
})
export class CitationBadgeComponent {
  @Input({ required: true }) citation!: CitationEvent;

  get icon(): string {
    return { observation: 'bi-activity', nursing_note: 'bi-journal-text', protocol: 'bi-book' }
      [this.citation.source_type] ?? 'bi-file-text';
  }

  get badgeClass(): string {
    return { observation: 'citation-obs', nursing_note: 'citation-note', protocol: 'citation-proto' }
      [this.citation.source_type] ?? 'citation-obs';
  }

  get scoreLabel(): string {
    return (this.citation.score * 100).toFixed(0) + '%';
  }

  get tooltip(): string {
    return `${this.citation.source_type.replace('_', ' ')} · ${this.citation.timestamp ?? 'unknown'} · ${this.scoreLabel}`;
  }
}
