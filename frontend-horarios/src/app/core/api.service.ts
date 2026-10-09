import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { firstValueFrom, Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ErrorSistema } from './supabase.service';

/** Base path of the asignacion module in the FastAPI backend */
const BASE = `${environment.apiUrl}/asignacion`;

/** Error body the API sends for DB/permission errors (same shape PostgREST used) */
interface ApiErrorDetail {
  message: string;
  code?: string | null;
  hint?: string | null;
}

/**
 * HTTP client for `/api/asignacion/...` that returns promises and turns API
 * errors into `ErrorSistema`, so pages keep showing the same messages they
 * showed with Supabase (duplicate, in use, no permission, trigger messages...).
 */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  get<T>(path: string, params?: Record<string, string | number | boolean | readonly (string | number | boolean)[]>): Promise<T> {
    return this.run(this.http.get<T>(`${BASE}${path}`, { params }));
  }

  /** Binary download (e.g. a photo); the interceptor adds the Bearer token */
  getBlob(path: string): Promise<Blob> {
    return this.run(this.http.get(`${BASE}${path}`, { responseType: 'blob' }));
  }

  /** Multipart upload (the browser sets the content type and boundary) */
  postForm<T>(path: string, form: FormData): Promise<T> {
    return this.run(this.http.post<T>(`${BASE}${path}`, form));
  }

  post<T>(path: string, body: unknown = {}): Promise<T> {
    return this.run(this.http.post<T>(`${BASE}${path}`, body));
  }

  patch<T>(path: string, body: unknown): Promise<T> {
    return this.run(this.http.patch<T>(`${BASE}${path}`, body));
  }

  put<T>(path: string, body: unknown): Promise<T> {
    return this.run(this.http.put<T>(`${BASE}${path}`, body));
  }

  delete(path: string): Promise<void> {
    return this.run(this.http.delete<void>(`${BASE}${path}`));
  }

  private async run<T>(request: Observable<T>): Promise<T> {
    try {
      return await firstValueFrom(request);
    } catch (e) {
      throw toErrorSistema(e);
    }
  }
}

/** Converts an HTTP error into the app's readable error */
function toErrorSistema(e: unknown): unknown {
  if (!(e instanceof HttpErrorResponse)) return e;
  const detail: unknown = e.error?.detail;
  if (detail && typeof detail === 'object' && !Array.isArray(detail) && 'message' in detail) {
    const { message, code, hint } = detail as ApiErrorDetail;
    return new ErrorSistema({ message, code: code ?? undefined, hint: hint ?? null });
  }
  if (typeof detail === 'string') {
    return new ErrorSistema({ message: detail, code: e.status === 403 ? '42501' : undefined });
  }
  if (e.status === 0) return new ErrorSistema({ message: 'No hay conexión con el servidor. Intente de nuevo.' });
  if (e.status === 422) return new ErrorSistema({ message: 'Hay datos inválidos en el formulario.' });
  return new ErrorSistema({
    message: 'No se pudo cargar la información. Intente de nuevo; si sigue igual, avise al administrador.',
  });
}
