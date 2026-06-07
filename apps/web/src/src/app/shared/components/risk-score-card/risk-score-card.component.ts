import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PatientRiskCard } from '../../../core/state/app.store';

@Component({
  selector: 'cm-risk-score-card',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="patient-card d-flex align-items-center gap-3"
         [class.active]="active"
         [class]="'patient-card ' + (active ? 'active' : '')"
         (click)="selected.emit(patient)"
         role="button">

      <!-- NEWS2 score circle -->
      <div class="news2-badge flex-shrink-0"
           [class]="'news2-badge bg-risk-' + patient.riskLevel">
        <span [class]="'risk-' + patient.riskLevel">{{ patient.news2Score }}</span>
      </div>

      <!-- Patient info -->
      <div class="flex-grow-1 min-w-0">
        <div class="d-flex align-items-center gap-2">
          <span class="fw-500 text-light" style="font-size:13px">{{ patient.patientName }}</span>
          @if (patient.anomalyDetected) {
            <i class="bi bi-exclamation-triangle-fill risk-high anomaly-flash" style="font-size:10px" title="Vitals anomaly"></i>
          }
        </div>
        <div class="d-flex align-items-center gap-2 mt-1">
          <span class="text-secondary" style="font-size:11px">
            <i class="bi bi-hospital me-1"></i>Bed {{ patient.wardBed }}
          </span>
          <span class="badge rounded-pill"
                style="font-size:9px;font-weight:500"
                [class]="'bg-risk-' + patient.riskLevel">
            <span [class]="'risk-' + patient.riskLevel">{{ patient.riskLevel | titlecase }}</span>
          </span>
        </div>
      </div>

      <!-- Arrow indicator when active -->
      @if (active) {
        <i class="bi bi-chevron-right text-primary flex-shrink-0" style="font-size:12px"></i>
      }
    </div>
  `,
})
export class RiskScoreCardComponent {
  @Input({ required: true }) patient!: PatientRiskCard;
  @Input() active = false;
  @Output() selected = new EventEmitter<PatientRiskCard>();
}
