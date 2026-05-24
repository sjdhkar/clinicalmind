/**
 * WardDashboardComponent — real-time ward patient overview.
 * Risk scores update live via SignalR (WebSocket) pushed from the .NET gateway.
 */
import {
  ChangeDetectionStrategy, Component, inject, OnInit,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { AppStore, PatientRiskCard } from '../../core/state/app.store';
import { RiskScoreCardComponent } from '../../shared/components/risk-score-card/risk-score-card.component';
import { ChatComponent } from '../chat/chat.component';

@Component({
  selector: 'cm-ward-dashboard',
  standalone: true,
  imports: [CommonModule, RiskScoreCardComponent, ChatComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="dashboard">

      <!-- Ward patient list -->
      <aside class="patient-list">
        <header class="list-header">
          <span class="list-title">Ward patients</span>
          <span class="critical-badge" [class.visible]="criticalCount() > 0">
            {{ criticalCount() }} critical
          </span>
        </header>

        @for (patient of patients(); track patient.patientId) {
          <cm-risk-score-card
            [patient]="patient"
            [active]="activePatientId() === patient.patientId"
            (selected)="selectPatient(patient)" />
        }

        @if (patients().length === 0) {
          <p class="empty">No patients loaded</p>
        }
      </aside>

      <!-- AI chat panel (right side) -->
      <main class="chat-area">
        @if (activePatientId()) {
          <cm-chat />
        } @else {
          <div class="no-patient">
            <p>Select a patient to begin</p>
          </div>
        }
      </main>

    </div>
  `,
  styles: [`
    .dashboard { display: flex; height: 100vh; overflow: hidden; }
    .patient-list {
      width: 280px; flex-shrink: 0;
      border-right: 0.5px solid var(--color-border-tertiary);
      overflow-y: auto;
      background: var(--color-background-secondary);
    }
    .list-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 1rem; border-bottom: 0.5px solid var(--color-border-tertiary);
      position: sticky; top: 0; background: var(--color-background-secondary);
    }
    .list-title { font-size: 13px; font-weight: 500; color: var(--color-text-secondary); }
    .critical-badge {
      font-size: 11px; background: var(--color-background-danger);
      color: var(--color-text-danger); border-radius: 10px;
      padding: 2px 8px; opacity: 0; transition: opacity 0.2s;
    }
    .critical-badge.visible { opacity: 1; }
    .chat-area { flex: 1; overflow: hidden; }
    .no-patient {
      display: flex; align-items: center; justify-content: center;
      height: 100%; color: var(--color-text-tertiary); font-size: 14px;
    }
    .empty { padding: 1rem; font-size: 13px; color: var(--color-text-tertiary); }
  `],
})
export class WardDashboardComponent implements OnInit {
  protected readonly store = inject(AppStore);
  protected readonly patients = this.store.patients;
  protected readonly activePatientId = this.store.activePatientId;
  protected readonly criticalCount = () =>
    this.store.criticalPatients().length;

  ngOnInit(): void {
    // In production: load patients + connect SignalR for real-time risk updates
    this.loadDemoPatients();
  }

  selectPatient(patient: PatientRiskCard): void {
    this.store.selectPatient(patient.patientId, 'enc-' + patient.patientId);
  }

  private loadDemoPatients(): void {
    this.store.setPatients([
      { patientId: 'p001', patientName: 'J. Smith', wardBed: 'A-12', news2Score: 7, riskLevel: 'high', lastUpdated: new Date(), anomalyDetected: true },
      { patientId: 'p002', patientName: 'M. Patel', wardBed: 'A-14', news2Score: 2, riskLevel: 'low', lastUpdated: new Date(), anomalyDetected: false },
      { patientId: 'p003', patientName: 'R. Kumar', wardBed: 'B-03', news2Score: 5, riskLevel: 'medium', lastUpdated: new Date(), anomalyDetected: false },
      { patientId: 'p004', patientName: 'S. Jones', wardBed: 'B-07', news2Score: 9, riskLevel: 'critical', lastUpdated: new Date(), anomalyDetected: true },
    ]);
  }
}
