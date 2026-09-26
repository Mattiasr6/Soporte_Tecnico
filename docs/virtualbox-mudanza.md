# Mudanza upds → VirtualBox (PC del aula)

El host GPU (`server-mattias`, 100.78.144.4) **se queda** corriendo llama-server.
Solo la VM se muda. El link Tailscale las vuelve a unir.

## Importar en VirtualBox (scadsp04)

1. Copiar `upds-virtualbox.vmdk` al Windows.
2. VirtualBox → Nueva → Linux/Debian 64-bit, 4 GB RAM, 2+ CPU.
3. **Usar un archivo de disco existente** → el `.vmdk`.
4. Red → **Adaptador puente** (recomendado, obtiene IP LAN) o NAT con reenvío
   `host 8011 → guest 8011` si solo se demo en ese PC.
5. Arrancar. Usuario: `mattias`.

## Primer arranque (checklist, en la VM)

1. `tailscale status` — si pide login: `tailscale up` (cuenta Mattiasr6@).
   **Anota la NUEVA IP Tailscale** (ya no será 100.90.209.98).
2. Avisar al host para abrir firewall a la nueva IP:
   `sudo ufw allow from <NUEVA_IP> to any port 8081 comment 'llama-server VM aula'`
3. En `~/Soporte_Tecnico2/frontend-django/.env`: agregar la nueva IP a
   `DJANGO_ALLOWED_HOSTS` (coma separada) y `sudo systemctl restart soporte-web-ia`.
4. `LLAMA_URL` no cambia: sigue `http://100.78.144.4:8081` (el host no se mueve).
5. Verificar: `curl localhost:5012/health` → ok; abrir `http://<NUEVA_IP>:8011/`.

## Si no hay internet en el aula

- Tailscale necesita internet para coordinar (luego el tráfico puede ir directo).
- Sin internet: edita `LLAMA_URL` a la IP LAN del host si comparten red física,
  o presenta con el video de respaldo (USB).

## Vuelta atrás

El qcow2 original sigue intacto en el host KVM. `virsh start MINIOS-MATTIAS`
lo devuelve todo como estaba.
