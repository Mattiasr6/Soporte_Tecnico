import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { firstValueFrom, Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ErrorSistema } from './errores';

/** Base path of the asignacion module in the FastAPI backend */
const BASE = `${environment.apiUrl}/asignacion`;

/** Error body the API sends for DB/permission errors: `{message, code, hint}` */
interface ApiErrorDetail {
  message: string;
  code?: string | null;
  hint?: string | null;
}

/**
 * HTTP client for `/api/asignacion/...` that returns promises and turns API
 * errors into `ErrorSistema`, so pages show readable messages (duplicate,
 * in use, no permission, trigger messages...).
 */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  /** Base path the relative `path` of every call is appended to */
  protected readonly base: string = BASE;

  get<T>(path: string, params?: Record<string, string | number | boolean | readonly (string | number | boolean)[]>): Promise<T> {
    return this.run(this.http.get<T>(`${this.base}${path}`, { params }));
  }

  /** Binary download (e.g. a photo); the interceptor adds the Bearer token */
  getBlob(path: string, params?: Record<string, string | number | boolean>): Promise<Blob> {
    return this.run(this.http.get(`${this.base}${path}`, { params, responseType: 'blob' }));
  }

  /** Multipart upload (the browser sets the content type and boundary) */
  postForm<T>(path: string, form: FormData): Promise<T> {
    return this.run(this.http.post<T>(`${this.base}${path}`, form));
  }

  post<T>(path: string, body: unknown = {}): Promise<T> {
    return this.run(this.http.post<T>(`${this.base}${path}`, body));
  }

  patch<T>(path: string, body: unknown): Promise<T> {
    return this.run(this.http.patch<T>(`${this.base}${path}`, body));
  }

  put<T>(path: string, body: unknown): Promise<T> {
    return this.run(this.http.put<T>(`${this.base}${path}`, body));
  }

  delete(path: string): Promise<void> {
    return this.run(this.http.delete<void>(`${this.base}${path}`));
  }

  private async run<T>(request: Observable<T>): Promise<T> {
    try {
      return await firstValueFrom(request);
    } catch (e) {
      throw toErrorSistema(e);
    }
  }
}

/**
 * Same client for the rest of the FastAPI routes (`/api/usuarios/...`,
 * `/api/auth/...`): same error handling, and the interceptor adds the token.
 */
@Injectable({ providedIn: 'root' })
export class ApiRaizService extends ApiService {
  protected override readonly base: string = environment.apiUrl;
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
