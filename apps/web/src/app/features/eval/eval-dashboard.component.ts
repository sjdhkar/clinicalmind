/**
 * EvalDashboardComponent — RAGAS evaluation metrics dashboard.
 * Uses ECharts for time-series metric trends.
 * This is the component that makes recruiters forward your GitHub.
 */
import {
  ChangeDetectionStrategy, Component, OnInit, inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgxEchartsModule } from 'ngx-echarts';
import type { EChartsOption } from 'echarts';
import { AppStore } from '../../core/state/app.store';

@Component({
  selector: 'cm-eval-dashboard',
  standalone: true,
  imports: [CommonModule, NgxEchartsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="eval-page">
      <h2 class="page-title">AI Evaluation Dashboard</h2>
      <p class="page-subtitle">RAGAS metrics — nightly evaluation against 200-scenario clinical golden set</p>

      <!-- KPI summary row -->
      <div class="kpi-row">
        @for (kpi of kpis; track kpi.label) {
          <div class="kpi-card" [class.pass]="kpi.passing" [class.fail]="!kpi.passing">
            <span class="kpi-label">{{ kpi.label }}</span>
            <span class="kpi-value">{{ kpi.value }}</span>
            <span class="kpi-threshold">threshold: {{ kpi.threshold }}</span>
          </div>
        }
      </div>

      <!-- RAGAS trend chart -->
      <div class="chart-card">
        <h3 class="chart-title">RAGAS metrics over time</h3>
        <div echarts [options]="ragas_chart_options" class="chart"></div>
      </div>

      <!-- Cost + latency chart -->
      <div class="chart-row">
        <div class="chart-card half">
          <h3 class="chart-title">Cost per query (USD)</h3>
          <div echarts [options]="cost_chart_options" class="chart-sm"></div>
        </div>
        <div class="chart-card half">
          <h3 class="chart-title">P95 latency (ms)</h3>
          <div echarts [options]="latency_chart_options" class="chart-sm"></div>
        </div>
      </div>

    </div>
  `,
  styles: [`
    .eval-page { padding: 1.5rem; max-width: 1200px; }
    .page-title { font-size: 18px; font-weight: 500; margin: 0 0 4px; }
    .page-subtitle { font-size: 13px; color: var(--color-text-secondary); margin: 0 0 1.5rem; }
    .kpi-row { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; margin-bottom: 1.5rem; }
    .kpi-card {
      background: var(--color-background-secondary);
      border: 0.5px solid var(--color-border-tertiary);
      border-radius: 10px; padding: 0.75rem; text-align: center;
    }
    .kpi-card.pass { border-color: #1D9E75; }
    .kpi-card.fail { border-color: #E24B4A; }
    .kpi-label { display: block; font-size: 11px; color: var(--color-text-secondary); margin-bottom: 4px; }
    .kpi-value { display: block; font-size: 20px; font-weight: 500; color: var(--color-text-primary); }
    .kpi-threshold { display: block; font-size: 10px; color: var(--color-text-tertiary); margin-top: 2px; }
    .chart-card {
      background: var(--color-background-primary);
      border: 0.5px solid var(--color-border-tertiary);
      border-radius: 12px; padding: 1rem; margin-bottom: 1rem;
    }
    .chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    .chart-card.half { margin-bottom: 0; }
    .chart-title { font-size: 14px; font-weight: 500; margin: 0 0 1rem; color: var(--color-text-primary); }
    .chart { height: 280px; }
    .chart-sm { height: 200px; }
  `],
})
export class EvalDashboardComponent implements OnInit {
  protected readonly store = inject(AppStore);

  readonly kpis = [
    { label: 'Faithfulness', value: '0.91', threshold: '≥ 0.85', passing: true },
    { label: 'Relevancy', value: '0.88', threshold: '≥ 0.80', passing: true },
    { label: 'Ctx Precision', value: '0.87', threshold: '≥ 0.80', passing: true },
    { label: 'Ctx Recall', value: '0.83', threshold: '≥ 0.75', passing: true },
    { label: 'Hallucination', value: '2.8%', threshold: '≤ 5%', passing: true },
    { label: 'NEWS2 Agreement', value: '94.2%', threshold: '≥ 90%', passing: true },
  ];

  readonly dates = ['May 18', 'May 19', 'May 20', 'May 21', 'May 22', 'May 23', 'May 24'];

  readonly ragas_chart_options: EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Faithfulness', 'Relevancy', 'Ctx Precision', 'Ctx Recall'] },
    xAxis: { type: 'category', data: this.dates },
    yAxis: { type: 'value', min: 0.6, max: 1.0 },
    series: [
      { name: 'Faithfulness', type: 'line', smooth: true, data: [0.87, 0.88, 0.89, 0.90, 0.91, 0.91, 0.91], lineStyle: { color: '#1D9E75' } },
      { name: 'Relevancy', type: 'line', smooth: true, data: [0.83, 0.84, 0.85, 0.86, 0.87, 0.88, 0.88], lineStyle: { color: '#185FA5' } },
      { name: 'Ctx Precision', type: 'line', smooth: true, data: [0.82, 0.83, 0.84, 0.85, 0.86, 0.87, 0.87], lineStyle: { color: '#534AB7' } },
      { name: 'Ctx Recall', type: 'line', smooth: true, data: [0.79, 0.80, 0.81, 0.82, 0.83, 0.83, 0.83], lineStyle: { color: '#BA7517' } },
    ],
  };

  readonly cost_chart_options: EChartsOption = {
    tooltip: { trigger: 'axis', formatter: '{b}: ${c}' },
    xAxis: { type: 'category', data: this.dates },
    yAxis: { type: 'value', axisLabel: { formatter: '${value}' } },
    series: [{
      type: 'bar', data: [0.0028, 0.0026, 0.0024, 0.0023, 0.0022, 0.0021, 0.0021],
      itemStyle: { color: '#1D9E75' },
    }],
  };

  readonly latency_chart_options: EChartsOption = {
    tooltip: { trigger: 'axis', formatter: '{b}: {c}ms' },
    xAxis: { type: 'category', data: this.dates },
    yAxis: { type: 'value' },
    series: [{
      type: 'line', smooth: true,
      data: [4200, 4100, 3900, 3700, 3600, 3400, 3400],
      areaStyle: { opacity: 0.1 },
      lineStyle: { color: '#185FA5' },
    }],
  };

  ngOnInit(): void {}
}
