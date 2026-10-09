import { ObjetoPerdido } from './modelos';

/**
 * Days an object can stay in custody before it shows as "vencido". Same rule
 * as the Soporte backend (`routers/novedades.py` `_estado_efectivo`): an object
 * still pending whose registration date is more than 90 days old. It is
 * computed, never stored; the object can still be delivered.
 */
export const DIAS_CUSTODIA = 90;

/** State shown on screen: the stored one plus the computed "vencido" */
export type EstadoObjetoVisible = 'en_custodia' | 'entregado' | 'vencido';

/** Whole days between two "YYYY-MM-DD" dates (calendar days, no time zone drift) */
function diasEntre(desde: string, hasta: string): number {
  return Math.round((Date.parse(`${hasta}T00:00:00Z`) - Date.parse(`${desde}T00:00:00Z`)) / 86_400_000);
}

/** "YYYY-MM-DD" of an instant in the given time zone */
function fechaEnZona(instante: string, zonaHoraria: string): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: zonaHoraria }).format(new Date(instante));
}

/**
 * Visible state of an object. `hoy` is today's "YYYY-MM-DD" in `zonaHoraria`,
 * the zone used to take the date the object was found.
 */
export function estadoVisible(o: ObjetoPerdido, hoy: string, zonaHoraria: string): EstadoObjetoVisible {
  if (o.estado !== 'en_custodia') return o.estado;
  return diasEntre(fechaEnZona(o.encontrado_en, zonaHoraria), hoy) > DIAS_CUSTODIA ? 'vencido' : 'en_custodia';
}
