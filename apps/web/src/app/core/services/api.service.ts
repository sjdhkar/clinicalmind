/**
 * ApiService — typed HTTP client for the .NET gateway.
 */
import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { PatientRiskCard, EvalMetric } from '../state/app.store';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api';

  getPatients(): Observable<PatientRiskCard[]> {
    return this.http.get<PatientRiskCard[]>(`${this.base}/patients`);
  }

  getEvalMetrics(): Observable<EvalMetric[]> {
    return this.http.get<EvalMetric[]>(`${this.base}/eval/metrics`);
  }
}
