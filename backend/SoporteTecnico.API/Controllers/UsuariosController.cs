using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using SoporteTecnico.API.Data;
using SoporteTecnico.API.DTOs;
using Microsoft.AspNetCore.SignalR;
using SoporteTecnico.API.Hubs;
using SoporteTecnico.API.Models;
using SoporteTecnico.API.Services;

namespace SoporteTecnico.API.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class UsuariosController : ControllerBase
{
    private readonly AppDbContext _db;
    private readonly IHubContext<AppHub> _hub;

    public UsuariosController(AppDbContext db, IHubContext<AppHub> hub)
    {
        _db = db;
        _hub = hub;
    }

    private int GetUserId() =>
        int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)!);

    [HttpGet]
    public async Task<ActionResult<List<UsuarioDto>>> GetAll()
    {
        var now = DateTime.UtcNow;
        var usuarios = await _db.Usuarios.Where(u => u.Role == "Tecnico").ToListAsync();
        var horarios = await _db.Horarios
            .Where(h => h.Mes == now.Month && h.Anio == now.Year).ToListAsync();

        var result = usuarios.Select(u => new UsuarioDto
        {
            Id = u.Id,
            DisplayName = u.DisplayName,
            Especialidad = u.Especialidad,
            Role = u.Role,
            EstadoActual = HorarioHelper.EstadoEfectivo(
                u.EstadoActual, horarios.FirstOrDefault(h => h.UsuarioId == u.Id))
        }).ToList();

        return Ok(result);
    }

    [HttpGet("me")]
    public async Task<ActionResult<UsuarioDto>> GetMe()
    {
        var userId = GetUserId();
        var now = DateTime.UtcNow;
        var usuario = await _db.Usuarios.FindAsync(userId);
        if (usuario is null) return NotFound("Usuario no registrado en el sistema.");

        var horario = await _db.Horarios
            .FirstOrDefaultAsync(h => h.UsuarioId == userId && h.Mes == now.Month && h.Anio == now.Year);

        return Ok(new UsuarioDto
        {
            Id = usuario.Id,
            DisplayName = usuario.DisplayName,
            Role = usuario.Role,
            EstadoActual = HorarioHelper.EstadoEfectivo(usuario.EstadoActual, horario)
        });
    }
    public record EspecialidadDto(string? Especialidad);

    [HttpPatch("{id}/especialidad")]
    public async Task<ActionResult> UpdateUserEspecialidad(int id, [FromBody] EspecialidadDto dto)
    {
        var user = await _db.Usuarios.FindAsync(GetUserId());
        if (user is null || (user.Role != "Jefe" && !user.CanViewDashboard)) return Forbid();

        var target = await _db.Usuarios.FindAsync(id);
        if (target is null) return NotFound();

        target.Especialidad = dto.Especialidad;
        await _db.SaveChangesAsync();
        return NoContent();
    }

    public record NotasDto(string? Contenido);

    [HttpGet("notas")]
    public async Task<ActionResult<NotasDto>> GetNotas()
    {
        var userId = GetUserId();
        var usuario = await _db.Usuarios.FirstOrDefaultAsync(u => u.Id == userId);
        if (usuario is null) return NotFound();
        return Ok(new NotasDto(usuario.Notas));
    }

    [HttpPut("notas")]
    public async Task<ActionResult> UpdateNotas([FromBody] NotasDto dto)
    {
        var userId = GetUserId();
        var usuario = await _db.Usuarios.FirstOrDefaultAsync(u => u.Id == userId);
        if (usuario is null) return NotFound();
        usuario.Notas = dto.Contenido;
        await _db.SaveChangesAsync();
        return NoContent();
    }

    [HttpPatch("estado")]
    public async Task<ActionResult> ToggleEstado([FromBody] UserStatusUpdateDto dto)
    {
        var userId = GetUserId();

        var usuario = await _db.Usuarios.FirstOrDefaultAsync(u => u.Id == userId);
        if (usuario is null) return NotFound("Usuario no registrado en el sistema.");

        if (!Enum.TryParse<EstadoUsuario>(dto.EstadoActual, true, out var nuevoEstado))
            return BadRequest("Estado inválido. Use: disponible, ocupado");

        if (nuevoEstado == EstadoUsuario.Ausente)
            return BadRequest("No puedes cambiarte a ausente manualmente.");

        usuario.EstadoActual = nuevoEstado;
        usuario.UpdatedAt = DateTime.UtcNow;
        await _db.SaveChangesAsync();

        string? colaboradorNombre = null;
        if (dto.ColaboradorId.HasValue)
        {
            var colab = await _db.Usuarios.FindAsync(dto.ColaboradorId.Value);
            colaboradorNombre = colab?.DisplayName;
        }

        var horario = await _db.Horarios
            .FirstOrDefaultAsync(h => h.UsuarioId == userId && h.Mes == DateTime.UtcNow.Month && h.Anio == DateTime.UtcNow.Year);
        var estadoEfectivo = HorarioHelper.EstadoEfectivo(usuario.EstadoActual, horario);

        await _hub.Clients.Group("all").SendAsync("StatusChanged", new
        {
            usuarioId = usuario.Id,
            nombre = usuario.DisplayName,
            estado = estadoEfectivo,
            motivo = dto.Motivo,
            colaboradorNombre,
            timestamp = DateTime.UtcNow.ToString("HH:mm")
        });

        return NoContent();
    }
}