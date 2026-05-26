import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideHttpClient(),
    provideRouter([
      {
        path: '',
        loadComponent: () =>
          import('./features/dashboard/ward-dashboard.component')
            .then(m => m.WardDashboardComponent),
      },
      {
        path: 'eval',
        loadComponent: () =>
          import('./features/eval/eval-dashboard.component')
            .then(m => m.EvalDashboardComponent),
      },
    ]),
  ],
};
