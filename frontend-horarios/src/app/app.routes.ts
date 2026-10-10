import { Routes } from '@angular/router';
import { exigirDashboard, exigirSoporte, exigirGestionAuxiliares, exigirInvitado, exigirOperacion, exigirSesion, soloSinSesion } from './core/guards';

/**
 * Rutas del sistema: 3 pantallas. Asignar, ceder y eventos se hacen desde
 * Inicio (la grilla del día) y se abren como paneles laterales.
 */
export const routes: Routes = [
  {
    path: 'login',
    canActivate: [soloSinSesion],
    loadComponent: () => import('./paginas/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'espera',
    title: 'Esperando rol',
    canActivate: [exigirInvitado],
    loadComponent: () => import('./paginas/login/espera.component').then((m) => m.EsperaComponent),
  },
  {
    path: '',
    canActivate: [exigirSesion],
    loadComponent: () => import('./paginas/layout/layout.component').then((m) => m.LayoutComponent),
    children: [
      { path: '', title: 'Inicio', loadComponent: () => import('./paginas/panel/panel.component').then((m) => m.PanelComponent) },
      { path: 'turno', title: 'Cerrar turno', canActivate: [exigirOperacion], loadComponent: () => import('./paginas/operacion/turno.component').then((m) => m.TurnoComponent) },
      { path: 'horario', title: 'Mi horario', canActivate: [exigirOperacion], loadComponent: () => import('./paginas/operacion/horario.component').then((m) => m.HorarioComponent) },
      { path: 'atenciones', title: 'Atenciones', canActivate: [exigirOperacion], loadComponent: () => import('./paginas/operacion/atenciones.component').then((m) => m.AtencionesComponent) },
      { path: 'objetos-perdidos', title: 'Objetos perdidos', canActivate: [exigirOperacion], loadComponent: () => import('./paginas/operacion/objetos-perdidos.component').then((m) => m.ObjetosPerdidosComponent) },
      { path: 'tablero-laboratorios', title: 'Tablero de laboratorios', loadComponent: () => import('./paginas/operacion/tablero-laboratorios.component').then((m) => m.TableroLaboratoriosComponent) },
      { path: 'novedades', title: 'Novedades', loadComponent: () => import('./paginas/operacion/novedades.component').then((m) => m.NovedadesComponent) },
      { path: 'cierres', title: 'Cierres de turno', canActivate: [exigirGestionAuxiliares], loadComponent: () => import('./paginas/operacion/cierres.component').then((m) => m.CierresComponent) },
      { path: 'timeline', title: 'Actividad del día', loadComponent: () => import('./paginas/operacion/timeline.component').then((m) => m.TimelineComponent) },
      { path: 'desempeno', title: 'Desempeño', canActivate: [exigirGestionAuxiliares], loadComponent: () => import('./paginas/operacion/desempeno.component').then((m) => m.DesempenoComponent) },
      { path: 'dashboard-laboratorios', title: 'Laboratorios por turno', canActivate: [exigirGestionAuxiliares], loadComponent: () => import('./paginas/operacion/dashboard-laboratorios.component').then((m) => m.DashboardLaboratoriosComponent) },
      { path: 'auxiliares', title: 'Auxiliares', canActivate: [exigirGestionAuxiliares], loadComponent: () => import('./paginas/operacion/auxiliares.component').then((m) => m.AuxiliaresComponent) },
      { path: 'laboratorios', title: 'Laboratorios', loadComponent: () => import('./paginas/laboratorios/laboratorios.component').then((m) => m.LaboratoriosComponent) },
      { path: 'software', title: 'Software de laboratorios', loadComponent: () => import('./paginas/laboratorios/software.component').then((m) => m.SoftwareComponent) },
      { path: 'registros', title: 'Registros', loadComponent: () => import('./paginas/registros/registros.component').then((m) => m.RegistrosComponent) },
      { path: 'auditoria', title: 'Auditoría', canActivate: [exigirDashboard], loadComponent: () => import('./paginas/auditoria/auditoria.component').then((m) => m.AuditoriaComponent) },
      { path: 'soporte/inicio', title: 'Inicio de Soporte', canActivate: [exigirSoporte], loadComponent: () => import('./paginas/soporte/inicio-soporte.component').then((m) => m.InicioSoporteComponent) },
      { path: 'soporte/atenciones', title: 'Atenciones de Soporte', canActivate: [exigirSoporte], loadComponent: () => import('./paginas/soporte/atenciones-soporte.component').then((m) => m.AtencionesSoporteComponent) },
      { path: 'soporte/atenciones/nueva', title: 'Nueva atención de Soporte', canActivate: [exigirSoporte], loadComponent: () => import('./paginas/soporte/nueva-atencion-soporte.component').then((m) => m.NuevaAtencionSoporteComponent) },
      { path: 'soporte/dashboard', title: 'Dashboard de Soporte', canActivate: [exigirDashboard], loadComponent: () => import('./paginas/soporte/dashboard-soporte.component').then((m) => m.DashboardSoporteComponent) },
      { path: 'soporte/jerarquia', title: 'Jerarquía de Soporte', canActivate: [exigirDashboard], loadComponent: () => import('./paginas/soporte/jerarquia-soporte.component').then((m) => m.JerarquiaSoporteComponent) },
      { path: 'soporte/horarios', title: 'Horarios de técnicos', canActivate: [exigirDashboard], loadComponent: () => import('./paginas/soporte/horarios-tecnicos.component').then((m) => m.HorariosTecnicosComponent) },
      { path: 'soporte/reportes', title: 'Reportes de Soporte', canActivate: [exigirDashboard], loadComponent: () => import('./paginas/soporte/reportes-soporte.component').then((m) => m.ReportesSoporteComponent) },
      { path: 'sugerencias', title: 'Sugerencias', loadComponent: () => import('./paginas/sugerencias/sugerencias.component').then((m) => m.SugerenciasComponent) },
      { path: 'cuenta/perfil', title: 'Perfil', loadComponent: () => import('./paginas/cuenta/perfil.component').then((m) => m.PerfilComponent) },
      { path: 'cuenta/notas', title: 'Bloc de notas', loadComponent: () => import('./paginas/cuenta/notas.component').then((m) => m.NotasComponent) },
      { path: 'configuracion', title: 'Configuración', loadComponent: () => import('./paginas/configuracion/configuracion.component').then((m) => m.ConfiguracionComponent) },
    ],
  },
  { path: '**', redirectTo: '' },
];
