using System.Collections.Concurrent;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.SignalR;
using Microsoft.EntityFrameworkCore;
using System.Security.Claims;
using SoporteTecnico.API.Data;
using SoporteTecnico.API.Models;
using SoporteTecnico.API.Services;

namespace SoporteTecnico.API.Hubs;

[Authorize]
public class AppHub : Hub
{
    private static readonly ConcurrentDictionary<string, int> ConnectedUsers = new();
    private readonly IServiceScopeFactory _scopeFactory;

    public AppHub(IServiceScopeFactory scopeFactory)
    {
        _scopeFactory = scopeFactory;
    }

    public override async Task OnConnectedAsync()
    {
        var userIdClaim = Context.User?.FindFirstValue(ClaimTypes.NameIdentifier);
        Console.WriteLine($"[SignalR] Connect: connectionId={Context.ConnectionId}, userIdClaim={userIdClaim}");
        await Groups.AddToGroupAsync(Context.ConnectionId, "all");

        if (userIdClaim is not null && int.TryParse(userIdClaim, out var usuarioId))
        {
            Console.WriteLine($"[SignalR] User {usuarioId} parsed OK");
            ConnectedUsers.TryAdd(Context.ConnectionId, usuarioId);

            using var scope = _scopeFactory.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            var user = await db.Usuarios.FindAsync(usuarioId);

            if (user is null)
            {
                Console.WriteLine($"[SignalR] User {usuarioId} NOT FOUND in DB");
            }
            else
            {
                Console.WriteLine($"[SignalR] User {user.DisplayName} estado={user.EstadoActual}");
                if (user.EstadoActual == EstadoUsuario.Ausente)
                {
                    user.EstadoActual = EstadoUsuario.Disponible;
                    user.UpdatedAt = DateTime.UtcNow;
                    await db.SaveChangesAsync();
                    Console.WriteLine($"[SignalR] {user.DisplayName} changed Ausente → Disponible");
                }

                var horario = await db.Horarios
                    .FirstOrDefaultAsync(h => h.UsuarioId == usuarioId && h.Mes == DateTime.UtcNow.Month && h.Anio == DateTime.UtcNow.Year);
                var estado = HorarioHelper.EstadoEfectivo(user.EstadoActual, horario);
                Console.WriteLine($"[SignalR] Broadcasting StatusChanged: {user.DisplayName} → {estado}");

                await Clients.Group("all").SendAsync("StatusChanged", new
                {
                    usuarioId = user.Id,
                    nombre = user.DisplayName,
                    estado,
                    motivo = (string?)null,
                    colaboradorNombre = (string?)null,
                    timestamp = DateTime.UtcNow.ToString("HH:mm")
                });
            }
        }
        else
        {
            Console.WriteLine($"[SignalR] No valid userIdClaim found in token");
        }

        await base.OnConnectedAsync();
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        Console.WriteLine($"[SignalR] Disconnect: connectionId={Context.ConnectionId}");
        if (ConnectedUsers.TryRemove(Context.ConnectionId, out var usuarioId))
        {
            // Solo marcar Ausente si es la ULTIMA conexion de este usuario
            bool tieneOtraConexion = ConnectedUsers.Values.Any(id => id == usuarioId);

            if (tieneOtraConexion)
            {
                Console.WriteLine($"[SignalR] User {usuarioId} aun tiene otra conexion activa, no se marca Ausente");
            }
            else
            {
                using var scope = _scopeFactory.CreateScope();
                var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                var user = await db.Usuarios.FindAsync(usuarioId);
                if (user is not null && user.EstadoActual == EstadoUsuario.Disponible)
                {
                    user.EstadoActual = EstadoUsuario.Ausente;
                    user.UpdatedAt = DateTime.UtcNow;
                    await db.SaveChangesAsync();
                    Console.WriteLine($"[SignalR] {user.DisplayName} → Ausente (ultima conexion cerrada)");

                    await Clients.Group("all").SendAsync("StatusChanged", new
                    {
                        usuarioId = user.Id,
                        nombre = user.DisplayName,
                        estado = "ausente",
                        motivo = (string?)null,
                        colaboradorNombre = (string?)null,
                        timestamp = DateTime.UtcNow.ToString("HH:mm")
                    });
                }
            }
        }

        await base.OnDisconnectedAsync(exception);
    }

    public async Task SendMessage(string message)
    {
        var nombre = Context.User?.FindFirstValue(ClaimTypes.Name) ?? "Desconocido";
        var role = Context.User?.FindFirstValue(ClaimTypes.Role) ?? "Tecnico";
        var timestamp = DateTime.UtcNow.ToString("HH:mm");

        await Clients.Group("all").SendAsync("ReceiveMessage", new
        {
            nombre,
            role,
            message,
            timestamp
        });
    }
}
