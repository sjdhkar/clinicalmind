/**
 * StreamingTextDirective — renders AI response tokens progressively.
 *
 * Usage: <p [appStreamText]="message.content" [isStreaming]="message.streaming">
 *
 * When isStreaming=true: shows blinking cursor after last token.
 * When isStreaming=false: removes cursor, response is complete.
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

    // Update text content
    if (changes['content']) {
      // Preserve cursor element, update text before it
      if (this.cursor && host.contains(this.cursor)) {
        host.removeChild(this.cursor);
      }
      host.textContent = this.content;
    }

    // Show or hide blinking cursor
    if (this.isStreaming) {
      if (!this.cursor) {
        this.cursor = this.renderer.createElement('span');
        this.renderer.addClass(this.cursor, 'streaming-cursor');
        this.renderer.setProperty(this.cursor, 'textContent', '▊');
        this.renderer.setStyle(this.cursor, 'animation', 'blink 1s step-end infinite');
        this.renderer.setStyle(this.cursor, 'opacity', '1');
        this.renderer.setStyle(this.cursor, 'color', 'var(--color-text-secondary)');
        this.renderer.setStyle(this.cursor, 'font-weight', '300');
      }
      host.appendChild(this.cursor);
    } else if (this.cursor && host.contains(this.cursor)) {
      host.removeChild(this.cursor);
      this.cursor = null;
    }
  }
}
