using System.Globalization;
using System.Text;
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using SoporteTecnico.API.Data;
using SoporteTecnico.API.DTOs;
using SoporteTecnico.API.Models;
using SoporteTecnico.API.Models;
using SoporteTecnico.API.Services;
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
                a.ColaboradorId,
                ColaboradorNombre = a.Colaborador != null ? a.Colaborador.DisplayName : null,
                a.FechaRegistro,
                a.FueraDeTurno,
                a.CreatedAt
            })
            .ToListAsync();
        return Ok(atenciones);
    }

    [HttpGet("stats")]
    public async Task<ActionResult> GetStats(
        [FromQuery] int? usuarioId,
        [FromQuery] int? desdeMes, [FromQuery] int? desdeAnio,
        [FromQuery] int? hastaMes, [FromQuery] int? hastaAnio)
    {
        var userId = GetUserId();
        var user = await _db.Usuarios.FindAsync(userId);
        if (user is null || (user.Role != "Jefe" && !user.CanViewDashboard))
            return Unauthorized();

        IQueryable<Atencion> query = _db.Atenciones.Include(a => a.Usuario);

        if (usuarioId.HasValue)
            query = query.Where(a => a.UsuarioId == usuarioId.Value);

        if (desdeAnio.HasValue && desdeMes.HasValue)
        {
            var desde = new DateOnly(desdeAnio.Value, desdeMes.Value, 1);
            query = query.Where(a => a.FechaRegistro >= desde);
        }

        if (hastaAnio.HasValue && hastaMes.HasValue)
        {
            var hasta = new DateOnly(hastaAnio.Value, hastaMes.Value,
                DateTime.DaysInMonth(hastaAnio.Value, hastaMes.Value));
            query = query.Where(a => a.FechaRegistro <= hasta);
        }

        var total = await query.CountAsync();
        var fueraDeTurno = await query.CountAsync(a => a.FueraDeTurno);

        var porTecnico = await query
            .GroupBy(a => new { a.UsuarioId, a.Usuario.DisplayName })
            .Select(g => new
            {
                usuarioId = g.Key.UsuarioId,
                displayName = g.Key.DisplayName,
                total = g.Count()
            })
            .OrderByDescending(g => g.total)
            .ToListAsync();

        var porCategoria = await query
            .GroupBy(a => a.Categoria)
            .Select(g => new
            {
                categoria = g.Key,
                total = g.Count()
            })
            .OrderByDescending(g => g.total)
            .ToListAsync();

        var porMes = await query
            .GroupBy(a => new { a.FechaRegistro.Year, a.FechaRegistro.Month })
            .Select(g => new
            {
                anio = g.Key.Year,
                mes = g.Key.Month,
                total = g.Count()
            })
            .OrderBy(g => g.anio).ThenBy(g => g.mes)
            .ToListAsync();

        var porArea = await query
            .GroupBy(a => a.AreaSolicitante)
            .Select(g => new
            {
                area = g.Key,
                total = g.Count()
            })
            .OrderByDescending(g => g.total)
            .Take(8)
            .ToListAsync();

        var asistenciasQuery = _db.Atenciones.Where(a => a.ColaboradorId != null);

        if (desdeAnio.HasValue && desdeMes.HasValue)
        {
            var desde = new DateOnly(desdeAnio.Value, desdeMes.Value, 1);
            asistenciasQuery = asistenciasQuery.Where(a => a.FechaRegistro >= desde);
        }

        if (hastaAnio.HasValue && hastaMes.HasValue)
        {
            var hasta = new DateOnly(hastaAnio.Value, hastaMes.Value,
                DateTime.DaysInMonth(hastaAnio.Value, hastaMes.Value));
            asistenciasQuery = asistenciasQuery.Where(a => a.FechaRegistro <= hasta);
        }

        if (usuarioId.HasValue)
            asistenciasQuery = asistenciasQuery.Where(a => a.ColaboradorId == usuarioId.Value);

        var asistencias = await asistenciasQuery
            .GroupBy(a => new { sid = a.ColaboradorId!.Value, a.Colaborador!.DisplayName })
            .Select(g => new
            {
                usuarioId = g.Key.sid,
                displayName = g.Key.DisplayName,
                total = g.Count()
            })
            .OrderByDescending(g => g.total)
            .ToListAsync();

        return Ok(new
        {
            total,
            fueraDeTurno,
            porTecnico,
            porCategoria,
            porMes,
            porArea,
            asistencias
        });
    }

    [HttpPut("{id}")]
    public async Task<ActionResult> Update(int id, [FromBody] UpdateAtencionDto dto)
    {
        var userId = GetUserId();
        var user = await _db.Usuarios.FindAsync(userId);
        if (user is null) return Unauthorized();

        var atencion = await _db.Atenciones.FindAsync(id);
        if (atencion is null) return NotFound();

        if (atencion.UsuarioId != userId && user.Role != "Jefe")
            return Forbid();

        if (dto.AreaSolicitante is not null) atencion.AreaSolicitante = dto.AreaSolicitante;
        if (dto.MedioSolicitud is not null) atencion.MedioSolicitud = dto.MedioSolicitud;
        if (dto.UsuarioSolicitante is not null) atencion.UsuarioSolicitante = dto.UsuarioSolicitante;
        if (dto.Categoria is not null) atencion.Categoria = dto.Categoria;
        if (dto.Descripcion is not null) atencion.Descripcion = dto.Descripcion;
        if (dto.Solucion is not null) atencion.Solucion = dto.Solucion;
        if (dto.Observaciones is not null) atencion.Observaciones = dto.Observaciones;
        if (dto.EnlaceApoyo is not null) atencion.EnlaceApoyo = dto.EnlaceApoyo;

        await _db.SaveChangesAsync();
        return NoContent();
    }

    [HttpDelete("{id}")]
    public async Task<ActionResult> Delete(int id)
    {
        var userId = GetUserId();
        var user = await _db.Usuarios.FindAsync(userId);
        if (user is null) return Unauthorized();

        var atencion = await _db.Atenciones.FindAsync(id);
        if (atencion is null) return NotFound();

        if (atencion.UsuarioId != userId && user.Role != "Jefe")
            return Forbid();

        _db.Atenciones.Remove(atencion);
        await _db.SaveChangesAsync();
        return NoContent();
    }

    [HttpPost("batch")]
    public async Task<ActionResult> CreateBatch([FromBody] AtencionBulkCreateDto dto)
    {
        var userId = GetUserId();

        var usuario = await _db.Usuarios.FirstOrDefaultAsync(u => u.Id == userId);
        if (usuario is null) return NotFound("Usuario no registrado en el sistema.");

        if (dto.Atenciones.Count == 0)
            return BadRequest("La lista de atenciones está vacía.");

        var now = DateTime.UtcNow;
        var horariosDelMes = await _db.Horarios
            .Where(h => h.UsuarioId == usuario.Id && h.Mes == now.Month && h.Anio == now.Year)
            .ToListAsync();
        var horarioUsuario = horariosDelMes.FirstOrDefault();

        var atenciones = dto.Atenciones.Select(a => new Atencion
        {
            UsuarioId = usuario.Id,
            AreaSolicitante = a.AreaSolicitante,
            MedioSolicitud = a.MedioSolicitud,
            UsuarioSolicitante = a.UsuarioSolicitante,
            Categoria = NormalizarCategoria(a.Categoria),
            Descripcion = a.Descripcion,
            Solucion = a.Solucion,
            Observaciones = a.Observaciones,
            EnlaceApoyo = a.EnlaceApoyo,
            ColaboradorId = a.ColaboradorId,
            FechaRegistro = a.FechaRegistro,
            FueraDeTurno = HorarioHelper.EstaFueraDeHorario(horarioUsuario, DateTime.UtcNow)
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
        var now_ic = DateTime.UtcNow;
        var horarioIc = await _db.Horarios
            .Where(h => h.UsuarioId == usuario.Id && h.Mes == now_ic.Month && h.Anio == now_ic.Year)
            .FirstOrDefaultAsync();

        if (file is null || file.Length == 0)
            return BadRequest("Debes subir un archivo CSV.");

        if (!file.FileName.EndsWith(".csv", StringComparison.OrdinalIgnoreCase))
            return BadRequest("El archivo debe tener extensión .csv");

        var atenciones = new List<Atencion>();
        var errores = new List<string>();

        // Detect encoding: prefer UTF-8, fallback a Latin-1 para Excel/Windows
        var stream = file.OpenReadStream();
        var preamble = new byte[4];
        var bytesRead = stream.Read(preamble, 0, 4);
        stream.Position = 0;
        Encoding encoding;
        if (bytesRead >= 3 && preamble[0] == 0xEF && preamble[1] == 0xBB && preamble[2] == 0xBF)
            encoding = Encoding.UTF8;   // BOM UTF-8
        else if (bytesRead >= 2 && preamble[0] == 0xFF && preamble[1] == 0xFE)
            encoding = Encoding.Unicode; // BOM UTF-16 LE
        else if (bytesRead >= 2 && preamble[0] == 0xFE && preamble[1] == 0xFF)
            encoding = Encoding.BigEndianUnicode;
        else
            encoding = Encoding.Latin1; // Excel/Windows sin BOM

        using var reader = new StreamReader(stream, encoding);
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
                Categoria = NormalizarCategoria(categoria),
                Descripcion = descripcion,
                Solucion = solucion,
                Observaciones = observaciones is "N/A" or "" ? null : observaciones,
                EnlaceApoyo = enlace is "N/A" or "" ? null : enlace,
                FechaRegistro = fecha,
                FueraDeTurno = HorarioHelper.EstaFueraDeHorario(horarioIc, DateTime.UtcNow)
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

    private static string NormalizarCategoria(string cat)
    {
        var map = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            ["impresion"] = "Impresión",
            ["cuentas"] = "Cuentas/Accesos",
            ["sistemas academicos"] = "Sistemas académicos",
        };
        return map.TryGetValue(cat.Trim(), out var norm) ? norm : cat;
    }
}
