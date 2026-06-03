/**
 * StreamingTextDirective — renders AI response tokens progressively.
 * Usage: <p [appStreamText]="message.content" [isStreaming]="message.streaming">
 */
import {
  Directive, ElementRef, Input, OnChanges, SimpleChanges, Renderer2,
} from '@angular/core';

@Directive({
  selector: '[appStreamText]',
  standalone: true,
})
export class StreamingTextDirective implements OnChanges {
  @Input('appStreamText') content = '';
  @Input() isStreaming = false;

  private cursor: HTMLElement | null = null;

  constructor(private el: ElementRef, private renderer: Renderer2) {}

  ngOnChanges(changes: SimpleChanges): void {
    const host: HTMLElement = this.el.nativeElement;

    if (changes['content']) {
      // Remove cursor before updating text
      if (this.cursor && host.contains(this.cursor)) {
        host.removeChild(this.cursor);
      }
      host.textContent = this.content;
    }

    if (this.isStreaming) {
      if (!this.cursor) {
        this.cursor = this.renderer.createElement('span') as HTMLElement;
        this.renderer.addClass(this.cursor, 'streaming-cursor');
        this.renderer.setProperty(this.cursor, 'textContent', '▊');
        this.renderer.setStyle(this.cursor, 'animation', 'blink 1s step-end infinite');
        this.renderer.setStyle(this.cursor, 'color', 'var(--color-text-secondary)');
      }
      // FIX: null-guard before appendChild — cursor is guaranteed non-null here
      // but TypeScript can't prove it from the assignment above without assertion
      if (this.cursor) {
        host.appendChild(this.cursor);
      }
    } else if (this.cursor && host.contains(this.cursor)) {
      host.removeChild(this.cursor);
      this.cursor = null;
    }
  }
}
