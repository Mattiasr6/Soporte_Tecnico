import { inject, Injectable, signal } from '@angular/core';
import { Atencion, EstadoAtencion, FallaPc, FichaReparacion, HorarioTurno, PcBajaCierre, Perfil, ReporteTurno, RotacionSabado, SolicitudBaja, TareaReporte, TurnoCodigo, TurnoProgramado, TurnoTrabajo } from './modelos';
import { AuthService } from './auth.service';
import { ApiService } from './api.service';
import { comprimirFoto } from './fotos';
import { aMinutos } from './fechas';

/**
 * Turno que corre a una hora 'HH:MM': entre los que la contienen, el que
 * empezó último (los turnos se solapan); si ninguno, el último que empezó.
 */
export function turnoDeLaHora(horarios: HorarioTurno[], hora: string): TurnoCodigo | null {
  const m = aMinutos(hora);
  const empezados = horarios.filter((h) => aMinutos(h.hora_inicio) <= m)
    .sort((a, b) => aMinutos(b.hora_inicio) - aMinutos(a.hora_inicio));
  const enCurso = empezados.find((h) => m < aMinutos(h.hora_fin));
  return (enCurso ?? empezados[0] ?? [...horarios].sort((a, b) => aMinutos(b.hora_inicio) - aMinutos(a.hora_inicio))[0])?.turno ?? null;
}

/** 85 -> '1 h 25 min' */
export function textoRetraso(minutos: number): string {
  const h = Math.floor(minutos / 60);
  const m = minutos % 60;
  return [h ? `${h} h` : '', m || !h ? `${m} min` : ''].filter(Boolean).join(' ');
}

/**
 * Turno vigente y próximo de un auxiliar, según sus turnos programados.
 * `hoy` es 'YYYY-MM-DD' (hora de La Paz). Compara las fechas como texto.
 */
export function turnosDeHoy(programados: TurnoProgramado[], perfilId: string, hoy: string):
  { actual: TurnoProgramado | null; proximo: TurnoProgramado | null } {
  const mios = programados.filter((t) => t.perfil_id === perfilId).sort((a, b) => a.desde.localeCompare(b.desde));
  const actual = [...mios].reverse().find((t) => t.desde <= hoy) ?? null;
  const proximo = mios.find((t) => t.desde > hoy) ?? null;
  return { actual, proximo };
}

/** Columns the API does not accept on write (id, timestamps and embeds) */
const NO_ESCRIBIBLES = ['id', 'creado_en', 'actualizado_en', 'ambiente', 'pc', 'docente', 'autor'];

/** Only the writable columns of a ticket */
function escribibles(fila: Partial<Atencion>): Record<string, unknown> {
  const datos = { ...fila } as Record<string, unknown>;
  for (const k of NO_ESCRIBIBLES) delete datos[k];
  return datos;
}

/** Filtros de la lista de atenciones / mantenimiento */
export interface FiltroOperacion {
  desde?: string;
  hasta?: string;
  estado?: string;
  ambienteId?: number | null;
  /** Tickets que registró o en los que colaboró este perfil */
  participante?: string;
}

/**
 * Operación de auxiliares: turno actual, pase de turno, atenciones y
 * mantenimiento. Mantiene en memoria el turno abierto y los pendientes.
 */
@Injectable({ providedIn: 'root' })
export class OperacionService {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);

  /** Turno abierto ahora (null si no hay ninguno) */
  readonly turnoActual = signal<TurnoTrabajo | null>(null);
  /** Último turno cerrado (para el pase de turno) */
  readonly ultimoCerrado = signal<TurnoTrabajo | null>(null);
  /** Catálogo de fallas (se carga con cargarFallas) */
  readonly fallas = signal<FallaPc[]>([]);
  /** Hora de inicio y fin de cada turno (se cargan con cargarHorarios) */
  readonly horarios = signal<HorarioTurno[]>([]);
  /** Atenciones sin resolver que vienen arrastradas (pase de turno) */
  readonly pendientes = signal<Atencion[]>([]);
  readonly cargando = signal(false);

  /** Refresca el turno actual, el último cerrado y los pendientes */
  async refrescar(): Promise<void> {
    this.cargando.set(true);
    try {
      const [estado, pend] = await Promise.all([
        this.api.get<{ abierto: TurnoTrabajo | null; ultimo_cerrado: TurnoTrabajo | null }>('/turnos-trabajo/estado'),
        this.api.get<Atencion[]>('/atenciones/arrastradas'),
      ]);
      this.turnoActual.set(estado.abierto);
      this.ultimoCerrado.set(estado.ultimo_cerrado);
      this.pendientes.set(pend);
    } finally {
      this.cargando.set(false);
    }
  }

  /** Abre un turno (falla si ya hay uno abierto, por el índice único) */
  async abrirTurno(turno: TurnoCodigo, esSabado: boolean, notas: string): Promise<void> {
    await this.api.post('/turnos-trabajo', { turno, es_sabado_rotativo: esSabado, notas: notas.trim() || null });
    await this.refrescar();
  }

  /** Cierra el turno dejando la nota de pase */
  async cerrarTurno(id: number, notas: string): Promise<void> {
    await this.api.post(`/turnos-trabajo/${id}/cierre`, { notas: notas.trim() || null });
    await this.refrescar();
  }

  // ----- Atenciones -----

  /** Lista de atenciones con filtros (para reportes) */
  listarAtenciones(filtro: FiltroOperacion = {}): Promise<Atencion[]> {
    const params: Record<string, string | number> = {};
    if (filtro.desde) params['desde'] = filtro.desde;
    if (filtro.hasta) params['hasta'] = filtro.hasta;
    if (filtro.estado) params['estado'] = filtro.estado;
    if (filtro.ambienteId) params['ambiente_id'] = filtro.ambienteId;
    if (filtro.participante) params['participante'] = filtro.participante;
    return this.api.get<Atencion[]>('/atenciones', params);
  }

  /** Crea o actualiza una atención */
  async guardarAtencion(fila: Partial<Atencion>): Promise<void> {
    const datos = escribibles(fila);
    if (fila.id) await this.api.patch(`/atenciones/${fila.id}`, datos);
    else await this.api.post('/atenciones', [datos]);
    await this.refrescar();
  }

  /** Crea varios tickets de una vez (una tarea hecha en varias PCs) */
  /** Crea tickets y devuelve su id y PC */
  async crearAtenciones(filas: Partial<Atencion>[]): Promise<{ id: number; pc_id: number | null }[]> {
    if (!filas.length) return [];
    const creados = await this.api.post<{ id: number; pc_id: number | null }[]>('/atenciones', filas.map(escribibles));
    await this.refrescar();
    return creados;
  }

  /** Cambia el estado de PCs (ticket = false si ya queda registrado en otro ticket, ej. un correctivo) */
  async cambiarEstadoPcs(ids: number[], estado: string, detalle: string, ticket = true): Promise<void> {
    if (!ids.length) return;
    await this.api.post('/ambiente-pcs/estado', { ids, estado, detalle, ticket });
  }

  /** Crea la PC docente y `cantidad` PCs numeradas en un laboratorio (fn_generar_pcs); devuelve cuántas creó */
  async generarPcs(ambienteId: number, cantidad: number): Promise<number> {
    const r = await this.api.post<{ creadas: number }>(`/ambientes/${ambienteId}/pcs/generar`, { cantidad });
    return r.creadas;
  }

  // ----- Fichas de reparación -----

  /** Catálogo de fallas (todas; la ficha muestra solo las activas) */
  async cargarFallas(): Promise<FallaPc[]> {
    const lista = await this.api.get<FallaPc[]>('/fallas-pc');
    this.fallas.set(lista);
    return lista;
  }

  /** Agrega una falla al catálogo (admin y encargado) */
  async agregarFalla(nombre: string, categoria: FallaPc['categoria']): Promise<void> {
    const orden = Math.max(0, ...this.fallas().filter((f) => f.categoria === categoria).map((f) => f.orden)) + 1;
    await this.api.post('/fallas-pc', { nombre: nombre.trim(), categoria, orden });
    await this.cargarFallas();
  }

  async actualizarFalla(id: number, cambios: Partial<Pick<FallaPc, 'nombre' | 'categoria' | 'activo'>>): Promise<void> {
    await this.api.patch(`/fallas-pc/${id}`, cambios);
    await this.cargarFallas();
  }

  /** Guarda las fichas: un ticket correctivo por PC y su cambio de estado */
  async registrarReparaciones(fichas: FichaReparacion[], colaboradores: string[] = [], prioridad = 2): Promise<number> {
    const r = await this.api.post<{ registradas: number }>('/reparaciones', { fichas, colaboradores, prioridad });
    await this.refrescar();
    return r.registradas;
  }

  /** Solicitudes de baja pendientes (las resuelve admin/encargado) */
  solicitudesBaja(): Promise<SolicitudBaja[]> {
    return this.api.get<SolicitudBaja[]>('/solicitudes-baja', { estado: 'pendiente' });
  }

  /** Pide la baja de PCs (si ya hay una pendiente para esa PC, no se repite) */
  async solicitarBaja(pcIds: number[], motivo: string, atencionPorPc: Map<number, number> = new Map()): Promise<void> {
    const pendientes = new Set((await this.solicitudesBaja()).map((s) => s.pc_id));
    const filas = pcIds.filter((id) => !pendientes.has(id))
      .map((pc_id) => ({ pc_id, motivo, atencion_id: atencionPorPc.get(pc_id) ?? null }));
    if (!filas.length) return;
    await this.api.post('/solicitudes-baja', filas);
  }

  async resolverBaja(id: number, aprobar: boolean, respuesta: string | null): Promise<void> {
    await this.api.post(`/solicitudes-baja/${id}/resolver`, { aprobar, respuesta });
  }

  /** Aplica los mismos cambios a varios tickets */
  async actualizarAtenciones(ids: number[], cambios: Partial<Atencion>): Promise<void> {
    if (!ids.length) return;
    await this.api.patch('/atenciones', { ids, cambios: escribibles(cambios) });
  }

  /** Cambia el estado de varios tickets (ej. todo un lote) */
  async cambiarEstadoAtenciones(ids: number[], estado: EstadoAtencion): Promise<void> {
    const resuelto = estado === 'resuelto';
    await this.api.patch('/atenciones', {
      ids,
      cambios: {
        estado,
        resuelto_por: resuelto ? this.auth.perfil()?.id ?? null : null,
        resuelto_en: resuelto ? new Date().toISOString() : null,
      },
    });
    await this.refrescar();
  }

  async eliminarAtenciones(ids: number[]): Promise<void> {
    if (!ids.length) return;
    await this.api.delete(`/atenciones?${ids.map((id) => `id=${encodeURIComponent(id)}`).join('&')}`);
    await this.refrescar();
  }

  /** Cambia el estado de una atención (resuelta marca autor y fecha) */
  async cambiarEstadoAtencion(a: Atencion, estado: EstadoAtencion): Promise<void> {
    await this.cambiarEstadoAtenciones([a.id], estado);
  }

  async eliminarAtencion(id: number): Promise<void> {
    await this.eliminarAtenciones([id]);
  }

  // ----- Reporte de turno -----

  /** Últimos reportes de turno con sus tareas */
  listarReportes(limite = 15): Promise<ReporteTurno[]> {
    return this.api.get<ReporteTurno[]>('/reportes-turno', { limite });
  }

  /** Tareas que ningún turno marcó como hechas todavía (las más viejas primero) */
  tareasPendientes(): Promise<TareaReporte[]> {
    return this.api.get<TareaReporte[]>('/reporte-tareas/pendientes');
  }

  /** Guarda el reporte del turno con sus tareas pendientes y su foto (opcional) */
  async crearReporte(turno: TurnoCodigo, novedades: string, tareas: { descripcion: string; ambiente_id: number | null }[],
    foto: File | null = null): Promise<void> {
    const creado = await this.api.post<ReporteTurno>('/reportes-turno', {
      turno, novedades: novedades.trim() || null, auxiliar_id: this.auth.perfil()?.id ?? null, tareas,
    });
    if (!foto) return;
    try {
      await this.subirFotoReporte(creado.id, foto);
    } catch (e) {
      // Que no quede un reporte sin la foto que se pidió: se deshace y se reintenta entero
      await this.api.delete(`/reportes-turno/${creado.id}`).catch(() => undefined);
      throw new Error(`No se pudo subir la foto: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  /** PCs que el usuario dio de baja desde un momento (las que saldrán en su cierre) */
  async misBajasDesde(desde: string): Promise<PcBajaCierre[]> {
    if (!this.auth.perfil()?.id) return [];
    type Fila = { etiqueta: string; motivo_baja: string | null; estado_detalle: string | null; estado_en: string; ambiente: { codigo: string } | null };
    const data = await this.api.get<Fila[]>('/ambiente-pcs/mis-bajas', { desde });
    return data.map((p) => ({
      etiqueta: p.etiqueta, lab: p.ambiente?.codigo ?? null, motivo: p.motivo_baja ?? p.estado_detalle, en: p.estado_en,
    }));
  }

  /** Comprime y sube la foto del cierre de un reporte */
  private async subirFotoReporte(reporteId: number, archivo: File): Promise<void> {
    const blob = await comprimirFoto(archivo);
    const form = new FormData();
    form.append('foto', new File([blob], 'foto.jpg', { type: 'image/jpeg' }));
    await this.api.postForm(`/reportes-turno/${reporteId}/foto`, form);
  }

  /** URLs locales (blob) de las fotos de cierre vigentes: ruta -> url */
  private urlsFotos: string[] = [];

  /**
   * Descarga las fotos de cierre de estos reportes (con el token de la sesión,
   * un <img src> no puede mandarlo) y devuelve ruta -> URL local. Libera las
   * URLs de la carga anterior. Una foto que no baja simplemente no se muestra.
   */
  async firmarFotosReporte(reportes: ReporteTurno[]): Promise<Map<string, string>> {
    for (const url of this.urlsFotos) URL.revokeObjectURL(url);
    this.urlsFotos = [];
    const mapa = new Map<string, string>();
    await Promise.all(reportes.filter((r) => r.foto_path).map(async (r) => {
      try {
        const url = URL.createObjectURL(await this.api.getBlob(`/reportes-turno/${r.id}/foto`));
        this.urlsFotos.push(url);
        mapa.set(r.foto_path!, url);
      } catch {
        /* sin foto: no se muestra */
      }
    }));
    return mapa;
  }

  /** Borra las fotos de cierre vencidas (después de las 12:00); la descripción se queda */
  async limpiarFotosReporte(): Promise<void> {
    await this.api.post('/reportes-turno/fotos/limpiar');
  }

  /** Marca (o desmarca) una tarea como hecha (la API registra quién y cuándo) */
  async marcarTarea(id: number, hecha: boolean): Promise<void> {
    await this.api.patch(`/reporte-tareas/${id}`, { hecha });
  }

  /**
   * Edita un reporte: turno, novedades y sus tareas pendientes (cambia las
   * existentes, agrega las nuevas y quita las que se borraron). Las tareas
   * hechas no se tocan.
   */
  async actualizarReporte(r: ReporteTurno, turno: TurnoCodigo, novedades: string,
    tareas: { id?: number; descripcion: string; ambiente_id: number | null }[]): Promise<void> {
    await this.api.patch(`/reportes-turno/${r.id}`, { turno, novedades: novedades.trim() || null });
    await this.api.put(`/reportes-turno/${r.id}/tareas`,
      tareas.map((t) => ({ id: t.id ?? null, descripcion: t.descripcion, ambiente_id: t.ambiente_id })));
  }

  async eliminarReporte(id: number): Promise<void> {
    await this.api.delete(`/reportes-turno/${id}`);
  }

  // ----- Auxiliares y rotación -----

  /** Lista de auxiliares (rol auxiliar) para el apartado Auxiliares */
  listarAuxiliares(): Promise<Perfil[]> {
    return this.api.get<Perfil[]>('/auxiliares', { rol: 'auxiliar' });
  }

  /** Active auxiliares and encargados (team screen: who is encargado) */
  listarEquipo(): Promise<Perfil[]> {
    return this.api.get<Perfil[]>('/auxiliares', { rol: ['auxiliar', 'encargado'], activo: true });
  }

  /** Personal de operación activo (auxiliares, técnicos y encargados), para elegir colaboradores */
  listarPersonalOperacion(): Promise<Perfil[]> {
    return this.api.get<Perfil[]>('/auxiliares', { rol: ['auxiliar', 'tecnico', 'encargado'], activo: true });
  }

  /** Asigna turno habitual y sábado rotativo (admin/encargado) vía fn_asignar_turno */
  async asignarTurno(usuarioId: string, turno: TurnoCodigo | null, sabado: boolean): Promise<void> {
    await this.api.put(`/auxiliares/${usuarioId}/turno`, { turno, sabado });
  }

  /** Rotación de sábados ordenada por fecha */
  listarRotacion(): Promise<RotacionSabado[]> {
    return this.api.get<RotacionSabado[]>('/rotacion-sabados');
  }

  async guardarRotacion(fila: Partial<RotacionSabado>): Promise<void> {
    const datos: Record<string, unknown> = {};
    for (const k of ['fecha', 'auxiliar_id', 'turno', 'nota'] as const) if (k in fila) datos[k] = fila[k];
    if (fila.id) await this.api.patch(`/rotacion-sabados/${fila.id}`, datos);
    else await this.api.post('/rotacion-sabados', datos);
  }

  /** Horario de cada turno, en orden de inicio */
  async cargarHorarios(): Promise<HorarioTurno[]> {
    const lista = await this.api.get<HorarioTurno[]>('/horarios-turno');
    this.horarios.set(lista);
    return lista;
  }

  /** Cambia el horario de los turnos (admin y encargado) */
  async guardarHorarios(lista: HorarioTurno[]): Promise<void> {
    const guardados = await this.api.put<HorarioTurno[]>('/horarios-turno',
      lista.map((h) => ({ turno: h.turno, hora_inicio: h.hora_inicio, hora_fin: h.hora_fin })));
    this.horarios.set(guardados);
  }

  /** Turnos programados de todos los auxiliares (más recientes primero) */
  listarTurnosProgramados(): Promise<TurnoProgramado[]> {
    return this.api.get<TurnoProgramado[]>('/turnos-programados');
  }

  /** Programa turnos de varios auxiliares desde una fecha (si ya existe esa fecha, la cambia) */
  async programarTurnos(filas: { perfil_id: string; turno: TurnoCodigo }[], desde: string): Promise<void> {
    if (!filas.length) return;
    await this.api.put('/turnos-programados', { desde, filas });
  }

  async eliminarTurnoProgramado(id: number): Promise<void> {
    await this.api.delete(`/turnos-programados/${id}`);
  }

  async eliminarRotacion(id: number): Promise<void> {
    await this.api.delete(`/rotacion-sabados/${id}`);
  }
}
