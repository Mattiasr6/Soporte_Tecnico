import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { BorradorSoporteService, ItemBorradorSoporte } from '../../core/borrador-soporte.service';
import { NotificacionesService } from '../../core/notificaciones.service';
import {
  ArbolJerarquia, AtencionSoporte, NuevaAtencionSoporte, SoporteService, UsuarioSoporte,
} from '../../core/soporte.service';
import { BorradorSoporteListaComponent } from './borrador-soporte-lista.component';
import { NuevaAtencionSoporteFormComponent, PedidoRegistro } from './nueva-atencion-soporte-form.component';
import { destinosDeArbol } from './selector-area-soporte.component';

/**
 * Nueva atención de Soporte. Igual que Django `nueva_vista`: se arma una lista
 * (agregar, editar, quitar) y se registra toda junta con un solo
 * POST /api/atenciones/batch; con la lista vacía se registra el formulario
 * directamente. La lista vive en `BorradorSoporteService` (por usuario, en
 * localStorage). La sugerencia de IA de Django quedó fuera por decisión
 * del usuario.
 */
@Component({
  selector: 'app-nueva-atencion-soporte',
  imports: [RouterLink, NuevaAtencionSoporteFormComponent, BorradorSoporteListaComponent],
  template: `
    <header class="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">Nueva atención</h1>
        <p class="text-sm text-slate-500">Sector → Dependencia → Área</p>
      </div>
      <a class="btn-secundario btn-sm" routerLink="/soporte/atenciones">Volver a la lista</a>
    </header>

    @if (cargando()) {
      <p class="text-sm text-slate-500">Cargando…</p>
    } @else if (errorCarga()) {
      <div class="tarjeta border-red-300 bg-red-50 p-4 text-sm text-red-800">
        No se pudo abrir el formulario: {{ errorCarga() }}
        <button class="btn-secundario btn-sm ml-2" (click)="cargar()">Reintentar</button>
      </div>
    } @else {
      <div class="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <section class="tarjeta p-4">
          @if (errorEnvio()) {
            <p class="mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">{{ errorEnvio() }}</p>
          }
          <app-nueva-atencion-soporte-form
            [destinos]="destinos()" [usuarios]="colaboradores()" [miUsuarioId]="miUsuarioId()"
            [inicial]="borrador.itemEditado()" [editando]="borrador.editando()" [cantidadLista]="borrador.items().length"
            [enviando]="enviando()"
            (agregar)="agregar($event)" (registrarPedido)="registrar($event)" (cancelarEdicion)="borrador.cancelarEdicion()" />
        </section>
        <div>
          <app-borrador-soporte-lista [items]="borrador.items()" [editando]="borrador.editando()" [recientes]="recientes()"
                                      (editar)="borrador.editar($event)" (quitar)="borrador.quitar($event)" />
        </div>
      </div>
    }
  `,
})
export class NuevaAtencionSoporteComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly soporte = inject(SoporteService);
  private readonly notificaciones = inject(NotificacionesService);
  private readonly router = inject(Router);
  protected readonly borrador = inject(BorradorSoporteService);

  protected readonly arbol = signal<ArbolJerarquia | null>(null);
  protected readonly usuarios = signal<UsuarioSoporte[]>([]);
  protected readonly recientes = signal<AtencionSoporte[]>([]);
  protected readonly cargando = signal(true);
  protected readonly errorCarga = signal('');
  protected readonly errorEnvio = signal('');
  protected readonly enviando = signal(false);

  protected readonly miUsuarioId = computed(() => this.auth.perfil()?.usuario_id ?? null);
  protected readonly destinos = computed(() => destinosDeArbol(this.arbol()));
  /** Django leaves the current user out of the collaborator list */
  protected readonly colaboradores = computed(() => this.usuarios().filter((u) => u.id !== this.miUsuarioId()));

  ngOnInit(): void {
    this.borrador.cargar();
    void this.cargar();
  }

  protected async cargar(): Promise<void> {
    this.cargando.set(true);
    this.errorCarga.set('');
    try {
      const [arbol, usuarios] = await Promise.all([this.soporte.arbol(), this.soporte.usuarios()]);
      this.usuarios.set(usuarios);
      this.arbol.set(arbol);
    } catch (e) {
      this.errorCarga.set(e instanceof Error ? e.message : String(e));
    } finally {
      this.cargando.set(false);
    }
    try {
      this.recientes.set(await this.soporte.recientes());
    } catch {
      // The recent list is only a reference; the form works without it
    }
  }

  protected agregar(item: ItemBorradorSoporte): void {
    this.errorEnvio.set('');
    this.borrador.guardarItem(item);
  }

  /** Sends the list, or the form row when the list is empty; the list survives a failure */
  protected async registrar(pedido: PedidoRegistro): Promise<void> {
    const filas = pedido.directo ? [pedido.directo] : this.borrador.items();
    if (!filas.length) {
      this.errorEnvio.set('Batch vacío.');
      return;
    }
    if (
      pedido.formularioConDatos &&
      !confirm('El formulario tiene datos que no agregaste a la lista. Se registrará solo la lista. ¿Continuar?')
    ) {
      return;
    }
    this.enviando.set(true);
    this.errorEnvio.set('');
    try {
      const r = await this.soporte.registrarLote(filas.map(sinRuta));
      if (!pedido.directo) this.borrador.vaciar();
      const n = r.registros_insertados;
      this.notificaciones.exito(n === 1 ? 'Atención registrada' : `${n} atenciones registradas`);
      await this.router.navigate(['/soporte/atenciones']);
    } catch (e) {
      // The batch is one transaction: nothing was stored, every row stays in the list
      this.errorEnvio.set(e instanceof Error ? e.message : 'No se pudo enviar');
    } finally {
      this.enviando.set(false);
    }
  }
}

/** Batch body without the display-only path */
function sinRuta({ ruta: _ruta, ...fila }: ItemBorradorSoporte): NuevaAtencionSoporte {
  return fila;
}
