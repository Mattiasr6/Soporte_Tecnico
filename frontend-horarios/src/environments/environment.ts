/**
 * Configuración del entorno.
 * Copie aquí los datos de su proyecto Supabase:
 *   Supabase > Project Settings > API
 *     - Project URL       -> supabaseUrl
 *     - anon public key   -> supabaseAnonKey
 */
export const environment = {
  /** Base URL of the FastAPI backend (dev: relative, served through proxy.conf.json) */
  apiUrl: '/api',
  supabaseUrl: 'https://nidfavlebczbiuugvtug.supabase.co',
  supabaseAnonKey: 'sb_publishable_jXVk86kLzVoPAG6teSXi6g_2pR7r_f_',
  /** Zona horaria de la universidad (para "ocupado ahora") */
  zonaHoraria: 'America/La_Paz',
};
