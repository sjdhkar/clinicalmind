/**
 * RiskScoreCardComponent — patient card with NEWS2 risk level colour coding.
 */
import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PatientRiskCard } from '../../../core/state/app.store';

@Component({
  selector: 'cm-risk-score-card',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="card"
      [class.active]="active"
      [attr.data-risk]="patient.riskLevel"
      (click)="selected.emit(patient)"
      role="button"
      [attr.aria-label]="'Patient ' + patient.patientName + ', risk ' + patient.riskLevel">

      <div class="card-left">
        <div class="risk-indicator" [attr.data-risk]="patient.riskLevel"></div>
        <div class="patient-info">
          <span class="patient-name">{{ patient.patientName }}</span>
          <span class="patient-bed">Bed {{ patient.wardBed }}</span>
        </div>
      </div>

      <div class="card-right">
        <div class="news2-score" [attr.data-risk]="patient.riskLevel">
          {{ patient.news2Score }}
        </div>
        @if (patient.anomalyDetected) {
          <span class="anomaly-dot" title="Vitals anomaly detected">⚡</span>
        }
      </div>

    </div>
  `,
  styles: [`
    .card {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0.75rem 1rem; cursor: pointer;
      border-bottom: 0.5px solid var(--color-border-tertiary);
      transition: background 0.15s;
    }
    .card:hover, .card.active { background: var(--color-background-primary); }
    .card-left { display: flex; align-items: center; gap: 10px; }
    .risk-indicator {
      width: 4px; height: 36px; border-radius: 2px; flex-shrink: 0;
    }
    .risk-indicator[data-risk="low"]      { background: #1D9E75; }
    .risk-indicator[data-risk="medium"]   { background: #EF9F27; }
    .risk-indicator[data-risk="high"]     { background: #D85A30; }
    .risk-indicator[data-risk="critical"] { background: #E24B4A; }
    .patient-name { font-size: 13px; font-weight: 500; color: var(--color-text-primary); display: block; }
    .patient-bed { font-size: 11px; color: var(--color-text-tertiary); }
    .card-right { display: flex; align-items: center; gap: 6px; }
    .news2-score {
      width: 32px; height: 32px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-size: 13px; font-weight: 500;
    }
    .news2-score[data-risk="low"]      { background: #E1F5EE; color: #0F6E56; }
    .news2-score[data-risk="medium"]   { background: #FAEEDA; color: #854F0B; }
    .news2-score[data-risk="high"]     { background: #FAECE7; color: #993C1D; }
    .news2-score[data-risk="critical"] { background: #FCEBEB; color: #A32D2D; }
    .anomaly-dot { font-size: 12px; }
  `],
})
export class RiskScoreCardComponent {
  @Input({ required: true }) patient!: PatientRiskCard;
  @Input() active = false;
  @Output() selected = new EventEmitter<PatientRiskCard>();
}
