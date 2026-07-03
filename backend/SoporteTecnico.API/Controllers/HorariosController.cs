using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using SoporteTecnico.API.Data;
using SoporteTecnico.API.Models;

namespace SoporteTecnico.API.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class HorariosController : ControllerBase
{
    private readonly AppDbContext _db;
    public HorariosController(AppDbContext db) => _db = db;

    private int GetUserId() => int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)!);
    private async Task<Usuario?> GetCurrentUser()
    {
        var id = GetUserId();
        return await _db.Usuarios.FindAsync(id);
    }

    public record HorarioDto(int? Id, int UsuarioId, string Nombre, string Label,
        string? HoraInicio1, string? HoraFin1, string? HoraInicio2, string? HoraFin2, int Mes, int Anio);

    public record AsignarDto(int UsuarioId, string Label,
        string? HoraInicio1, string? HoraFin1, string? HoraInicio2, string? HoraFin2, int Mes, int Anio);

    public record CoberturaDto(string Franja, string Hora, List<string> Tecnicos);

    [HttpGet]
    public async Task<ActionResult> GetAll([FromQuery] int? mes, [FromQuery] int? anio)
    {
        var user = await GetCurrentUser();
        if (user is null) return Unauthorized();
        var query = _db.Horarios.Include(h => h.Usuario).AsQueryable();
        if (mes.HasValue) query = query.Where(h => h.Mes == mes.Value);
        if (anio.HasValue) query = query.Where(h => h.Anio == anio.Value);
        if (user.Role != "Jefe") query = query.Where(h => h.UsuarioId == user.Id);

        var items = await query.OrderBy(h => h.Usuario.DisplayName)
            .Select(h => new HorarioDto(h.Id, h.UsuarioId, h.Usuario.DisplayName,
                h.Label, h.HoraInicio1, h.HoraFin1, h.HoraInicio2, h.HoraFin2, h.Mes, h.Anio))
            .ToListAsync();
        return Ok(items);
    }

    [HttpPost]
    public async Task<ActionResult> Asignar([FromBody] AsignarDto dto)
    {
        var user = await GetCurrentUser();
        if (user is null || (user.Role != "Jefe" && !user.CanViewDashboard))
            return Forbid();

        var tecnico = await _db.Usuarios.FindAsync(dto.UsuarioId);
        if (tecnico is null || tecnico.Role != "Tecnico")
            return BadRequest(new { error = "Tecnico no encontrado" });

        var existente = await _db.Horarios
            .FirstOrDefaultAsync(h => h.UsuarioId == dto.UsuarioId && h.Mes == dto.Mes && h.Anio == dto.Anio);

        if (existente is not null)
        {
            existente.Label = dto.Label;
            existente.HoraInicio1 = dto.HoraInicio1;
            existente.HoraFin1 = dto.HoraFin1;
            existente.HoraInicio2 = dto.HoraInicio2;
            existente.HoraFin2 = dto.HoraFin2;
        }
        else
        {
            _db.Horarios.Add(new Horario
            {
                UsuarioId = dto.UsuarioId,
                Label = dto.Label,
                HoraInicio1 = dto.HoraInicio1,
                HoraFin1 = dto.HoraFin1,
                HoraInicio2 = dto.HoraInicio2,
                HoraFin2 = dto.HoraFin2,
                Mes = dto.Mes,
                Anio = dto.Anio
            });
        }
        await _db.SaveChangesAsync();
        return NoContent();
    }

    [HttpDelete("{id}")]
    public async Task<ActionResult> Eliminar(int id)
    {
        var user = await GetCurrentUser();
        if (user is null || (user.Role != "Jefe" && !user.CanViewDashboard)) return Forbid();
        var horario = await _db.Horarios.FindAsync(id);
        if (horario is null) return NotFound();
        _db.Horarios.Remove(horario);
        await _db.SaveChangesAsync();
        return NoContent();
    }

    static bool TieneCobertura(string? inicio1, string? fin1, string? inicio2, string? fin2, string fInicio, string fFin)
    {
        if (inicio1 is null || fin1 is null) return false;
        bool b1 = string.Compare(inicio1, fFin) < 0 && string.Compare(fin1, fInicio) > 0;
        if (b1) return true;
        if (inicio2 is not null && fin2 is not null)
            return string.Compare(inicio2, fFin) < 0 && string.Compare(fin2, fInicio) > 0;
        return false;
    }

    [HttpGet("cobertura")]
    public async Task<ActionResult> GetCobertura([FromQuery] int? mes, [FromQuery] int? anio)
    {
        var user = await GetCurrentUser();
        if (user is null) return Unauthorized();

        var now = DateTime.UtcNow;
        var targetMes = mes ?? now.Month;
        var targetAnio = anio ?? now.Year;

        var horarios = await _db.Horarios
            .Include(h => h.Usuario)
            .Where(h => h.Mes == targetMes && h.Anio == targetAnio)
            .ToListAsync();

        var franjas = new (string nombre, string inicio, string fin)[]
        {
            ("Manana", "08:00", "12:00"),
            ("Medio dia", "12:00", "14:30"),
            ("Tarde", "14:30", "18:30"),
            ("Noche", "18:30", "20:00"),
        };

        var cobertura = franjas.Select(f => new CoberturaDto(
            f.nombre, $"{f.inicio} - {f.fin}",
            horarios.Where(h => TieneCobertura(h.HoraInicio1, h.HoraFin1, h.HoraInicio2, h.HoraFin2, f.inicio, f.fin))
                    .Select(h => h.Usuario.DisplayName).ToList()
        )).ToList();

        return Ok(new { mes = targetMes, anio = targetAnio, cobertura });
    }
}
