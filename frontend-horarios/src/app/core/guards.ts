import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

/** Exige sesión iniciada con perfil activo y con acceso (el Invitado va a la espera) */
export const exigirSesion: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  await auth.inicializar();
  if (!auth.perfil()?.activo) return router.createUrlTree(['/login']);
  return auth.esInvitado() ? router.createUrlTree(['/espera']) : true;
};

/** Pantalla de espera: solo para el Invitado (sin acceso todavía) */
export const exigirInvitado: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  await auth.inicializar();
  if (!auth.perfil()?.activo) return router.createUrlTree(['/login']);
  return auth.esInvitado() ? true : router.createUrlTree(['/']);
};

/** Edición académica: Jefe, Encargado, Decano */
export const exigirEdicion: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  await auth.inicializar();
  return auth.puedeEditar() ? true : router.createUrlTree(['/']);
};

/** Operación: Jefe, Encargado, Auxiliar, Técnico */
export const exigirOperacion: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  await auth.inicializar();
  return auth.puedeOperar() ? true : router.createUrlTree(['/']);
};

/** Gestión de auxiliares: Jefe, Encargado */
export const exigirGestionAuxiliares: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  await auth.inicializar();
  return auth.puedeGestionarAuxiliares() ? true : router.createUrlTree(['/']);
};

/** Reportes y auditoría: Jefe o usuario con dashboard */
export const exigirDashboard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  await auth.inicializar();
  return auth.puedeVerDashboard() ? true : router.createUrlTree(['/']);
};

/** Solo Jefe (administrador) */
export const exigirAdmin: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  await auth.inicializar();
  return auth.esAdmin() ? true : router.createUrlTree(['/']);
};

/** Si ya hay sesión, el login redirige al inicio */
export const soloSinSesion: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  await auth.inicializar();
  return auth.perfil()?.activo ? router.createUrlTree(['/']) : true;
};
