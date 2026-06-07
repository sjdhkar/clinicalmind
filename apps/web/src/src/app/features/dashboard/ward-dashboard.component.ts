import { ChangeDetectionStrategy, Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AppStore, PatientRiskCard } from '../../core/state/app.store';
import { ApiService } from '../../core/services/api.service';
import { ChatComponent } from '../chat/chat.component';

@Component({
  selector: 'cm-ward-dashboard',
  standalone: true,
  imports: [CommonModule, ChatComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host { display:block; height:calc(100vh - 56px); overflow:hidden; }
    .layout  { display:flex; height:100%; overflow:hidden; }
    .sidebar { width:272px; min-width:272px; display:flex; flex-direction:column;
               background:#161b27; border-right:1px solid #2d3748; overflow:hidden; }
    .sidebar-list { flex:1; overflow-y:auto; }
    .pt-card { display:flex; align-items:center; gap:12px; padding:12px 16px;
               cursor:pointer; border-left:3px solid transparent;
               border-bottom:1px solid #1e2433; transition:background .15s; }
    .pt-card:hover,.pt-card.active { background:#1e2840; }
    .pt-card.active { border-left-color:#3b82f6; }
    .n2c { width:40px; height:40px; border-radius:50%; display:flex;
           align-items:center; justify-content:center;
           font-weight:700; font-size:15px; flex-shrink:0; border:2px solid; }
    .main { flex:1; min-width:0; display:flex; flex-direction:column; overflow:hidden; }
    .pbar { flex-shrink:0; display:flex; align-items:center; justify-content:space-between;
            padding:10px 20px; background:#161b27;
            border-bottom:1px solid #2d3748; min-height:56px; }
    .chat-wrap { flex:1; min-height:0; display:flex; flex-direction:column; overflow:hidden; }
    .c-low      { color:#10b981!important; border-color:#10b981!important; background:rgba(16,185,129,.13)!important; }
    .c-medium   { color:#f59e0b!important; border-color:#f59e0b!important; background:rgba(245,158,11,.13)!important; }
    .c-high     { color:#f97316!important; border-color:#f97316!important; background:rgba(249,115,22,.13)!important; }
    .c-critical { color:#ef4444!important; border-color:#ef4444!important; background:rgba(239,68,68,.13)!important; }
    .rpill { font-size:10px; padding:2px 8px; border-radius:20px; border:1px solid; font-weight:500; }
    .pdot  { width:7px; height:7px; border-radius:50%; background:#10b981;
             display:inline-block; animation:pulse 2s infinite; }
    @keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.75)}}
  `],
  template: `
<div class="layout">

  <!-- SIDEBAR -->
  <aside class="sidebar">
    <div class="d-flex align-items-center justify-content-between px-3 py-2"
         style="background:#1a2035;border-bottom:1px solid #2d3748;flex-shrink:0">
      <span style="font-size:11px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.06em">
        <i class="bi bi-hospital me-2"></i>Ward Patients
      </span>
      @if(criticalCount()>0){
        <span class="badge rounded-pill bg-danger" style="font-size:9px">{{criticalCount()}} critical</span>
      }
    </div>

    <div class="sidebar-list">
      @if(patients().length===0){
        <div class="text-center py-5">
          <div class="spinner-border spinner-border-sm text-secondary mb-2"></div>
          <p class="text-secondary mb-0" style="font-size:12px">Loading…</p>
        </div>
      }
      @for(p of patients(); track p.patientId){
        <div class="pt-card" [class.active]="activePatientId()===p.patientId" (click)="select(p)">
          <div class="n2c flex-shrink-0" [class]="'c-'+p.riskLevel">{{p.news2Score}}</div>
          <div style="min-width:0;flex:1">
            <div class="d-flex align-items-center gap-1">
              <span style="font-size:13px;font-weight:500;color:#e2e8f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                {{p.patientName}}</span>
              @if(p.anomalyDetected){<i class="bi bi-exclamation-triangle-fill c-high" style="font-size:10px;flex-shrink:0"></i>}
            </div>
            <div class="d-flex align-items-center gap-2 mt-1">
              <span style="font-size:11px;color:#64748b"><i class="bi bi-geo-alt me-1"></i>{{p.wardBed}}</span>
              <span class="rpill" [class]="'c-'+p.riskLevel">{{p.riskLevel|titlecase}}</span>
            </div>
          </div>
          @if(activePatientId()===p.patientId){<i class="bi bi-chevron-right text-primary" style="font-size:11px;flex-shrink:0"></i>}
        </div>
      }
    </div>

    <div class="d-flex align-items-center gap-2 px-3 py-2"
         style="border-top:1px solid #2d3748;flex-shrink:0">
      <span class="pdot"></span>
      <span style="font-size:10px;color:#475569">Live monitoring</span>
    </div>
  </aside>

  <!-- MAIN -->
  <div class="main">
    @if(!activePatientId()){
      <div class="d-flex flex-column align-items-center justify-content-center h-100 gap-3">
        <div class="rounded-circle d-flex align-items-center justify-content-center"
             style="width:64px;height:64px;background:#1e2433;border:1px solid #2d3748">
          <i class="bi bi-arrow-left text-secondary" style="font-size:1.4rem"></i>
        </div>
        <div class="text-center">
          <p class="mb-1" style="font-size:14px;font-weight:500;color:#94a3b8">Select a patient</p>
          <p class="mb-0" style="font-size:12px;color:#475569">AI will analyse their clinical records</p>
        </div>
      </div>
    }@else{
      <!-- Patient bar -->
      <div class="pbar">
        @if(activePatient()){
          <div class="d-flex align-items-center gap-2 flex-wrap">
            <span style="font-size:14px;font-weight:600;color:#f1f5f9">{{activePatient()!.patientName}}</span>
            <span style="font-size:12px;color:#64748b">· Bed {{activePatient()!.wardBed}}</span>
            <span class="rpill" [class]="'c-'+activePatient()!.riskLevel">
              {{activePatient()!.riskLevel|titlecase}} Risk
            </span>
            @if(activePatient()!.anomalyDetected){
              <span class="c-high" style="font-size:11px"><i class="bi bi-activity me-1"></i>Anomaly</span>
            }
          </div>
          <div class="d-flex align-items-center gap-2">
            <span style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.04em">NEWS2</span>
            <div class="n2c" style="width:46px;height:46px;font-size:17px" [class]="'c-'+activePatient()!.riskLevel">
              {{activePatient()!.news2Score}}
            </div>
          </div>
        }
      </div>
      <!-- Chat fills remaining height -->
      <div class="chat-wrap"><cm-chat /></div>
    }
  </div>
</div>
  `,
})
export class WardDashboardComponent implements OnInit {
  protected readonly store           = inject(AppStore);
  protected readonly api             = inject(ApiService);
  protected readonly patients        = this.store.patients;
  protected readonly activePatientId = this.store.activePatientId;
  protected readonly activePatient   = this.store.activePatient;
  protected readonly criticalCount   = () => this.store.criticalPatients().length;

  ngOnInit(): void {
    this.api.getPatients().subscribe({
      next: p  => this.store.setPatients(p),
      error: () => this.store.setPatients([
        { patientId:'p001', patientName:'J. Smith', wardBed:'A-12', news2Score:7, riskLevel:'high',     lastUpdated:new Date(), anomalyDetected:true  },
        { patientId:'p002', patientName:'M. Patel', wardBed:'A-14', news2Score:2, riskLevel:'low',      lastUpdated:new Date(), anomalyDetected:false },
        { patientId:'p003', patientName:'R. Kumar', wardBed:'B-03', news2Score:4, riskLevel:'medium',   lastUpdated:new Date(), anomalyDetected:false },
        { patientId:'p004', patientName:'S. Jones', wardBed:'B-07', news2Score:9, riskLevel:'critical', lastUpdated:new Date(), anomalyDetected:true  },
      ]),
    });
  }

  select(p: PatientRiskCard): void {
    this.store.selectPatient(p.patientId, 'enc-' + p.patientId);
  }
}
