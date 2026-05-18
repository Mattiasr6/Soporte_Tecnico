using System.Globalization;
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using SoporteTecnico.API.Data;
using SoporteTecnico.API.DTOs;
using SoporteTecnico.API.Models;

namespace SoporteTecnico.API.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class AtencionesController : ControllerBase
{
    private readonly AppDbContext _db;

    public AtencionesController(AppDbContext db)
    {
        _db = db;
    }

    private int GetUserId() =>
        int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)!);

    [HttpGet]
    public async Task<ActionResult> GetAll([FromQuery] int? usuarioId)
    {
        var userId = GetUserId();
        var user = await _db.Usuarios.FindAsync(userId);
        if (user is null) return Unauthorized();

        IQueryable<Atencion> query = _db.Atenciones.Include(a => a.Usuario);

        if (user.Role == "Jefe" && usuarioId.HasValue)
            query = query.Where(a => a.UsuarioId == usuarioId.Value);
        else if (user.Role != "Jefe")
            query = query.Where(a => a.UsuarioId == userId);

        var atenciones = await query
            .OrderByDescending(a => a.FechaRegistro)
            .ThenByDescending(a => a.Id)
            .Select(a => new
            {
                a.Id,
                a.UsuarioId,
                UsuarioNombre = a.Usuario.DisplayName,
                a.AreaSolicitante,
                a.MedioSolicitud,
                a.UsuarioSolicitante,
                a.Categoria,
                a.Descripcion,
                a.Solucion,
                a.Observaciones,
                a.EnlaceApoyo,
                a.FechaRegistro,
                a.CreatedAt
            })
            .ToListAsync();

        return Ok(atenciones);
    }

    [HttpPost("batch")]
    public async Task<ActionResult> CreateBatch([FromBody] AtencionBulkCreateDto dto)
    {
        var userId = GetUserId();

        var usuario = await _db.Usuarios.FirstOrDefaultAsync(u => u.Id == userId);
        if (usuario is null) return NotFound("Usuario no registrado en el sistema.");

        if (dto.Atenciones.Count == 0)
            return BadRequest("La lista de atenciones está vacía.");

        var atenciones = dto.Atenciones.Select(a => new Atencion
        {
            UsuarioId = usuario.Id,
            AreaSolicitante = a.AreaSolicitante,
            MedioSolicitud = a.MedioSolicitud,
            UsuarioSolicitante = a.UsuarioSolicitante,
            Categoria = a.Categoria,
            Descripcion = a.Descripcion,
            Solucion = a.Solucion,
            Observaciones = a.Observaciones,
            EnlaceApoyo = a.EnlaceApoyo,
            FechaRegistro = a.FechaRegistro
        }).ToList();

        _db.Atenciones.AddRange(atenciones);
        await _db.SaveChangesAsync();

        return Ok(new { registrosInsertados = atenciones.Count });
    }

    [HttpPost("import-csv")]
    public async Task<ActionResult> ImportCsv(IFormFile file)
    {
        var userId = GetUserId();

        var usuario = await _db.Usuarios.FirstOrDefaultAsync(u => u.Id == userId);
        if (usuario is null) return NotFound("Usuario no registrado en el sistema.");

        if (file is null || file.Length == 0)
            return BadRequest("Debes subir un archivo CSV.");

        if (!file.FileName.EndsWith(".csv", StringComparison.OrdinalIgnoreCase))
            return BadRequest("El archivo debe tener extensión .csv");

        var atenciones = new List<Atencion>();
        var errores = new List<string>();

        using var reader = new StreamReader(file.OpenReadStream());
        var lineNumber = 0;
        while (await reader.ReadLineAsync() is string line)
        {
            lineNumber++;
            if (lineNumber == 1) continue;

            var parts = line.Split(';');
            if (parts.Length < 8) continue;

            if (!int.TryParse(parts[0].Trim(), out _)) continue;

            var area = parts[2].Trim();
            var medio = parts[4].Trim();
            var usuarioSol = parts[3].Trim();
            var categoria = parts[5].Trim();
            var descripcion = parts[6].Trim();
            var solucion = parts[7].Trim();
            var observaciones = parts.Length > 8 ? parts[8].Trim() : null;
            var enlace = parts.Length > 9 ? parts[9].Trim() : null;
            var fechaStr = parts[1].Trim();

            if (string.IsNullOrEmpty(area) || string.IsNullOrEmpty(descripcion) || string.IsNullOrEmpty(solucion))
            {
                errores.Add($"Línea {lineNumber}: faltan campos obligatorios");
                continue;
            }

            DateOnly fecha;
            if (!DateOnly.TryParseExact(fechaStr, "dd/MM/yyyy", CultureInfo.InvariantCulture, DateTimeStyles.None, out fecha))
                fecha = DateOnly.FromDateTime(DateTime.UtcNow);

            atenciones.Add(new Atencion
            {
                UsuarioId = usuario.Id,
                AreaSolicitante = area,
                MedioSolicitud = medio is "Presencial" or "Interno" or "WhatsApp" or "E-ticket" ? medio : "Interno",
                UsuarioSolicitante = usuarioSol is "ADM" or "BEC" or "DOC" ? usuarioSol : "ADM",
                Categoria = categoria,
                Descripcion = descripcion,
                Solucion = solucion,
                Observaciones = observaciones is "N/A" or "" ? null : observaciones,
                EnlaceApoyo = enlace is "N/A" or "" ? null : enlace,
                FechaRegistro = fecha
            });
        }

        if (atenciones.Count == 0)
            return BadRequest(new { error = "No se encontraron registros válidos en el CSV.", errores });

        _db.Atenciones.AddRange(atenciones);
        await _db.SaveChangesAsync();

        return Ok(new
        {
            registrosInsertados = atenciones.Count,
            errores = errores.Count > 0 ? errores : null
        });
    }
}
