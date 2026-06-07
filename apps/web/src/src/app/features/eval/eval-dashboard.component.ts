import { ChangeDetectionStrategy, Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'cm-eval-dashboard',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="container-fluid py-4 px-4" style="background:#0f1117;min-height:calc(100vh - 56px)">

      <!-- Header -->
      <div class="d-flex align-items-start justify-content-between mb-4">
        <div>
          <h5 class="text-light mb-1 fw-500">
            <i class="bi bi-graph-up-arrow me-2 text-primary"></i>AI Evaluation Dashboard
          </h5>
          <p class="text-secondary mb-0" style="font-size:12px">
            RAGAS metrics · 200-scenario clinical golden set · Updated nightly via CI/CD
          </p>
        </div>
        <span class="badge d-flex align-items-center gap-1"
              style="background:rgba(16,185,129,.15);color:#10b981;border:1px solid #10b981;font-size:11px">
          <span class="pulse-dot" style="width:6px;height:6px"></span>
          All thresholds passing
        </span>
      </div>

      <!-- KPI Cards -->
      <div class="row g-3 mb-4">
        @for (kpi of kpis; track kpi.label) {
          <div class="col-6 col-md-4 col-lg-2">
            <div class="metric-card" [class.pass]="kpi.passing" [class.fail]="!kpi.passing">
              <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">
                {{ kpi.label }}
              </div>
              <div class="metric-value" [style.color]="kpi.passing ? '#10b981' : '#ef4444'">
                {{ kpi.value }}
              </div>
              <div class="metric-bar">
                <div class="metric-bar-fill"
                     [style.width.%]="kpi.pct"
                     [style.background]="kpi.passing ? '#10b981' : '#ef4444'"></div>
              </div>
              <div style="font-size:10px;color:#64748b">
                threshold {{ kpi.threshold }}
                <i class="bi ms-1" [class]="kpi.passing ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger'"></i>
              </div>
            </div>
          </div>
        }
      </div>

      <div class="row g-3">
        <!-- Run history -->
        <div class="col-12 col-lg-8">
          <div class="cm-table">
            <div class="px-3 py-2 d-flex align-items-center justify-content-between"
                 style="border-bottom:1px solid #2d3748">
              <span style="font-size:12px;font-weight:500;color:#94a3b8">
                <i class="bi bi-clock-history me-2"></i>Evaluation Run History
              </span>
              <span class="badge" style="background:#1e3a5f;color:#60a5fa;font-size:10px">Last 5 runs</span>
            </div>
            <div class="table-responsive">
              <table class="table table-sm mb-0 cm-table">
                <thead>
                  <tr>
                    <th>Date</th><th>SHA</th><th>Faithfulness</th>
                    <th>Relevancy</th><th>Hallucination</th><th>P95</th><th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  @for (run of runs; track run.sha) {
                    <tr>
                      <td style="color:#94a3b8">{{ run.date }}</td>
                      <td><code style="color:#60a5fa;font-size:11px">{{ run.sha }}</code></td>
                      <td>
                        <div class="d-flex align-items-center gap-2">
                          <div style="width:40px;height:3px;background:#2d3748;border-radius:2px">
                            <div style="height:3px;border-radius:2px;background:#10b981"
                                 [style.width.%]="run.faithfulness * 100"></div>
                          </div>
                          {{ run.faithfulness }}
                        </div>
                      </td>
                      <td>{{ run.relevancy }}</td>
                      <td>{{ run.hallucination }}</td>
                      <td>{{ run.latency }}</td>
                      <td>
                        <span class="badge rounded-pill"
                              [style.background]="run.passed ? 'rgba(16,185,129,.15)' : 'rgba(239,68,68,.15)'"
                              [style.color]="run.passed ? '#10b981' : '#ef4444'"
                              [style.border]="'1px solid ' + (run.passed ? '#10b981' : '#ef4444')">
                          <i class="bi me-1" [class]="run.passed ? 'bi-check-lg' : 'bi-x-lg'"></i>
                          {{ run.passed ? 'PASS' : 'FAIL' }}
                        </span>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Cost breakdown -->
        <div class="col-12 col-lg-4">
          <div class="cm-table h-100">
            <div class="px-3 py-2" style="border-bottom:1px solid #2d3748">
              <span style="font-size:12px;font-weight:500;color:#94a3b8">
                <i class="bi bi-currency-dollar me-2"></i>Cost by Model
              </span>
            </div>
            <div class="p-3">
              @for (m of models; track m.name) {
                <div class="d-flex align-items-center justify-content-between py-2"
                     style="border-bottom:1px solid #1e2433">
                  <div>
                    <div style="font-size:12px;color:#e2e8f0">{{ m.name }}</div>
                    <div style="font-size:10px;color:#64748b">{{ m.pct }}% of queries</div>
                  </div>
                  <div class="text-end">
                    <div style="font-size:13px;font-weight:500" [style.color]="m.cost === '$0.00' ? '#10b981' : '#e2e8f0'">
                      {{ m.cost }}
                    </div>
                    <div style="font-size:10px" [style.color]="m.saving ? '#10b981' : '#64748b'">
                      {{ m.saving || 'per query' }}
                    </div>
                  </div>
                </div>
              }
              <div class="mt-3 p-2 text-center rounded"
                   style="background:rgba(16,185,129,.1);border:1px solid #10b981">
                <div style="font-size:11px;color:#64748b">vs. all-GPT-4o baseline</div>
                <div style="font-size:18px;font-weight:600;color:#10b981">76% cost saving</div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  `,
})
export class EvalDashboardComponent {
  readonly kpis = [
    { label: 'Faithfulness',    value: '0.91', threshold: '≥0.85', passing: true,  pct: 91 },
    { label: 'Relevancy',       value: '0.88', threshold: '≥0.80', passing: true,  pct: 88 },
    { label: 'Ctx Precision',   value: '0.87', threshold: '≥0.80', passing: true,  pct: 87 },
    { label: 'Ctx Recall',      value: '0.83', threshold: '≥0.75', passing: true,  pct: 83 },
    { label: 'Hallucination',   value: '2.8%', threshold: '≤5%',   passing: true,  pct: 72 },
    { label: 'NEWS2 Agreement', value: '94%',  threshold: '≥90%',  passing: true,  pct: 94 },
  ];

  readonly runs = [
    { date:'2025-05-24', sha:'e3a1f99', faithfulness:0.91, relevancy:0.88, hallucination:'2.8%', latency:'3.4s', passed:true },
    { date:'2025-05-23', sha:'a6780df', faithfulness:0.91, relevancy:0.88, hallucination:'2.9%', latency:'3.5s', passed:true },
    { date:'2025-05-22', sha:'f50bea9', faithfulness:0.90, relevancy:0.87, hallucination:'3.1%', latency:'3.6s', passed:true },
    { date:'2025-05-21', sha:'295e663', faithfulness:0.89, relevancy:0.86, hallucination:'3.4%', latency:'3.7s', passed:true },
    { date:'2025-05-20', sha:'3dee8fe', faithfulness:0.87, relevancy:0.84, hallucination:'4.1%', latency:'4.1s', passed:true },
  ];

  readonly models = [
    { name: 'Phi-3-mini (local)', pct: 38, cost: '$0.00',  saving: '100% saving' },
    { name: 'GPT-4o-mini',        pct: 41, cost: '$0.0004', saving: '92% saving'  },
    { name: 'GPT-4o',             pct: 21, cost: '$0.0050', saving: null          },
    { name: 'Blended average',    pct: 100,cost: '$0.0021', saving: null          },
  ];
}
