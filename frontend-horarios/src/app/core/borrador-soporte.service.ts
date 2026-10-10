import { computed, inject, Injectable, signal } from '@angular/core';
import { AuthService } from './auth.service';
import { NuevaAtencionSoporte } from './soporte.service';

/** A draft row: the batch body plus the área path, kept only to show it in the list */
export interface ItemBorradorSoporte extends NuevaAtencionSoporte {
  ruta: string;
}

/** What is persisted per user */
interface BorradorGuardado {
  items: ItemBorradorSoporte[];
  editando: number | null;
}

const PREFIJO_CLAVE = 'upds.soporte.borrador.';

/**
 * Batch draft of the "Nueva atención" screen. Django kept it in the server
 * session (`batch`, `edit_idx`); here it is a signal store persisted per
 * Soporte user in localStorage, so a reload or a new login keeps it. Storage
 * failures (private mode, quota) only lose persistence, never the screen.
 */
@Injectable({ providedIn: 'root' })
export class BorradorSoporteService {
  private readonly auth = inject(AuthService);

  readonly items = signal<ItemBorradorSoporte[]>([]);
  /** Index of the row loaded in the form, or null when adding */
  readonly editando = signal<number | null>(null);
  readonly itemEditado = computed(() => {
    const i = this.editando();
    return i === null ? null : (this.items()[i] ?? null);
  });

  private clave: string | null = null;

  /** Loads the current user's draft; call it when the screen opens */
  cargar(): void {
    const usuarioId = this.auth.perfil()?.usuario_id;
    this.clave = usuarioId ? `${PREFIJO_CLAVE}${usuarioId}` : null;
    const guardado = this.leer();
    this.items.set(guardado.items);
    this.editando.set(guardado.editando !== null && guardado.editando < guardado.items.length ? guardado.editando : null);
  }

  /** Adds a row, or replaces the one being edited (Django "agregar") */
  guardarItem(item: ItemBorradorSoporte): void {
    const i = this.editando();
    if (i !== null && i < this.items().length) {
      this.items.update((lista) => lista.map((x, j) => (j === i ? item : x)));
    } else {
      this.items.update((lista) => [...lista, item]);
    }
    this.editando.set(null);
    this.persistir();
  }

  editar(indice: number): void {
    if (indice < 0 || indice >= this.items().length) return;
    this.editando.set(indice);
    this.persistir();
  }

  cancelarEdicion(): void {
    this.editando.set(null);
    this.persistir();
  }

  /** Removes a row; any edit in progress is dropped, like Django "quitar" */
  quitar(indice: number): void {
    this.items.update((lista) => lista.filter((_, j) => j !== indice));
    this.editando.set(null);
    this.persistir();
  }

  vaciar(): void {
    this.items.set([]);
    this.editando.set(null);
    this.persistir();
  }

  private leer(): BorradorGuardado {
    const vacio: BorradorGuardado = { items: [], editando: null };
    if (!this.clave) return vacio;
    try {
      const datos = JSON.parse(localStorage.getItem(this.clave) ?? 'null') as Partial<BorradorGuardado> | null;
      if (!datos || !Array.isArray(datos.items)) return vacio;
      const items = datos.items.filter(
        (x): x is ItemBorradorSoporte => !!x && typeof x === 'object' && typeof x.descripcion === 'string' && typeof x.categoria === 'string',
      );
      return { items, editando: typeof datos.editando === 'number' ? datos.editando : null };
    } catch {
      return vacio;
    }
  }

  private persistir(): void {
    if (!this.clave) return;
    try {
      if (this.items().length === 0 && this.editando() === null) {
        localStorage.removeItem(this.clave);
      } else {
        localStorage.setItem(this.clave, JSON.stringify({ items: this.items(), editando: this.editando() }));
      }
    } catch {
      // Storage unavailable or full: the draft still lives in memory for this visit
    }
  }
}
