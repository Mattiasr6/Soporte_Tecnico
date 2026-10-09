/**
 * Error con mensaje en español a partir del error que devuelve la API
 * (`detail = {message, code, hint}`, códigos SQLSTATE de Postgres).
 */
export class ErrorSistema extends Error {
  /** Sugerencia que manda la base (campo HINT) */
  readonly sugerencia: string | null;

  constructor(error: { message: string; hint?: string | null; code?: string }) {
    super(traducirError(error));
    this.sugerencia = error.hint ?? null;
  }
}

/** Traduce códigos de error comunes a mensajes entendibles */
function traducirError(error: { message: string; code?: string }): string {
  switch (error.code) {
    case '23505': return 'Ya existe un registro con esos datos (valor duplicado).';
    case '23503': return 'No se puede completar: el registro está siendo usado por otros datos.';
    case '42501': return 'No tiene permisos para realizar esta acción.';
    default: return error.message;
  }
}
