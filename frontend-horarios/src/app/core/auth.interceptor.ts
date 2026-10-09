import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

/** Requests to the backend API (relative `/api/...` in dev, absolute in other envs) */
function isApiRequest(url: string): boolean {
  return url === environment.apiUrl || url.startsWith(`${environment.apiUrl}/`);
}

/** Login answers 401 for bad credentials: that must not be treated as an expired session */
function isLoginRequest(url: string): boolean {
  return url.split('?')[0] === `${environment.apiUrl}/auth/login`;
}

/**
 * Adds `Authorization: Bearer <token>` to API requests and, on 401,
 * drops the session and sends the user back to the login page.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  if (!isApiRequest(req.url)) return next(req);
  const auth = inject(AuthService);
  const token = auth.sesion();
  const request = token && !isLoginRequest(req.url) ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;
  return next(request).pipe(
    catchError((error: unknown) => {
      // Only expire the session that sent this request: a late 401 from an old token
      // must not wipe a session created by a newer login.
      const sameSession = auth.sesion() === token;
      if (error instanceof HttpErrorResponse && error.status === 401 && !isLoginRequest(req.url) && sameSession) {
        auth.sesionExpirada();
      }
      return throwError(() => error);
    }),
  );
};
