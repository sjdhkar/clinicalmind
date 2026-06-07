import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'cm-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <nav class="navbar navbar-dark px-3 py-0" style="height:56px">
      <a class="navbar-brand d-flex align-items-center gap-2" routerLink="/">
        <span class="pulse-dot"></span>
        ClinicalMind
        <span class="badge ms-1" style="background:#1d4ed8;font-size:10px;font-weight:400">AI</span>
      </a>
      <ul class="navbar-nav flex-row gap-1">
        <li class="nav-item">
          <a class="nav-link" routerLink="/" routerLinkActive="active-link" [routerLinkActiveOptions]="{exact:true}">
            <i class="bi bi-hospital me-1"></i>Ward
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link" routerLink="/eval" routerLinkActive="active-link">
            <i class="bi bi-graph-up me-1"></i>Eval
          </a>
        </li>
      </ul>
    </nav>
    <router-outlet />
  `,
})
export class AppComponent {}
