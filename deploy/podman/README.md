# Podman (espejo prod/dev)

‎| stack | api | web | horarios | pg |
‎|---|---|---|---|---|
‎| prod | 127.0.0.1:5002 | :8001 | — | :5433 |
‎| dev | 127.0.0.1:5012 | :8011 | — | :5434 |
‎| upds | 127.0.0.1:5013 | :8013 | :4213 | 127.0.0.1:5435 |

Mismos puertos que systemd hoy. Cero cambios de codigo.

## Gates antes del cutover
- [x] Backup prod 20261003 (2894 atenciones, verificado)
- [ ] Restore test en `soporte_test`
- [ ] Migraciones 0010-0015 a prod (dry-run primero)
- [ ] DNS apuntando + Caddy (`--profile edge`)

## Uso
‎```sh
‎cp .env.prod.example .env.prod  # completar secretos
‎podman-compose -f prod.compose.yml config   # validar sin prender
‎podman-compose -f prod.compose.yml up -d
‎podman-compose -f prod.compose.yml --profile edge up -d  # con borde HTTPS
‎```
‎Notas: `pgbackup` vuelca `db` (prod real). Dev usa `5434`;
‎al migrar dev hay que mover su `DATABASE_URL` de `:5433` a `:5434`.

UPDS (`upds.compose.yml`, proyecto `soporte-upds`): `horarios` es el build de
`frontend-horarios` servido por nginx en `:4213`, con `/api` proxied a `api:5013`
(mismo origen, sin CORS). `podman-compose --env-file .env.upds -f upds.compose.yml up -d --build horarios`.
