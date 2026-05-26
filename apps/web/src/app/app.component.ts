import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'cm-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="app-layout">

      <!-- Top navigation -->
      <nav class="navbar">
        <a class="navbar-brand" routerLink="/">
          <span class="brand-dot"></span>
          ClinicalMind
        </a>

        <ul class="navbar-nav">
          <li>
            <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}">
              Ward
            </a>
          </li>
          <li>
            <a routerLink="/eval" routerLinkActive="active">
              Eval Dashboard
            </a>
          </li>
        </ul>
      </nav>

      <!-- Page content -->
      <main class="app-content">
        <router-outlet />
      </main>

    </div>
  `,
})
export class AppComponent {}
