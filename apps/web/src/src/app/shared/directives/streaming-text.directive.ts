import { Directive, ElementRef, Input, OnChanges, SimpleChanges, Renderer2 } from '@angular/core';

@Directive({ selector: '[appStreamText]', standalone: true })
export class StreamingTextDirective implements OnChanges {
  @Input('appStreamText') content = '';
  @Input() isStreaming = false;
  private cursor: HTMLElement | null = null;

  constructor(private el: ElementRef, private renderer: Renderer2) {}

  ngOnChanges(changes: SimpleChanges): void {
    const host: HTMLElement = this.el.nativeElement;
    if (changes['content']) {
      if (this.cursor && host.contains(this.cursor)) host.removeChild(this.cursor);
      host.textContent = this.content;
    }
    if (this.isStreaming) {
      if (!this.cursor) {
        this.cursor = this.renderer.createElement('span') as HTMLElement;
        this.renderer.addClass(this.cursor, 'streaming-cursor');
        this.renderer.setProperty(this.cursor, 'textContent', '▊');
      }
      if (this.cursor) host.appendChild(this.cursor);
    } else if (this.cursor && host.contains(this.cursor)) {
      host.removeChild(this.cursor);
      this.cursor = null;
    }
  }
}
