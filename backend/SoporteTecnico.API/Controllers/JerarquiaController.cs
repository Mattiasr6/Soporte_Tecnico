using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using SoporteTecnico.API.Data;

namespace SoporteTecnico.API.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class JerarquiaController : ControllerBase
{
    private readonly AppDbContext _db;
    public JerarquiaController(AppDbContext db) => _db = db;

    [HttpGet("grupos-padres")]
    public async Task<ActionResult> GetGruposPadres() =>
        Ok(await _db.GruposPadres.OrderBy(g => g.Orden).ToListAsync());

    [HttpGet("grupos")]
    public async Task<ActionResult> GetGrupos([FromQuery] int? grupoPadreId)
    {
        var q = _db.Grupos.AsQueryable();
        if (grupoPadreId.HasValue) q = q.Where(g => g.GrupoPadreId == grupoPadreId.Value);
        return Ok(await q.OrderBy(g => g.Nombre).ToListAsync());
    }

    [HttpGet("areas")]
    public async Task<ActionResult> GetAreas([FromQuery] int? grupoPadreId, [FromQuery] int? grupoId)
    {
        var q = _db.Areas.Where(a => a.Activo).AsQueryable();
        if (grupoPadreId.HasValue) q = q.Where(a => a.GrupoPadreId == grupoPadreId.Value);
        if (grupoId.HasValue) q = q.Where(a => a.GrupoId == grupoId.Value);
        // si grupoId null y se pide solo por padre, incluir áreas directas (GrupoId null) y todas del padre
        return Ok(await q.OrderBy(a => a.Nombre).ToListAsync());
    }

    [HttpGet("arbol")]
    public async Task<ActionResult> GetArbol()
    {
        var padres = await _db.GruposPadres.OrderBy(g => g.Orden).ToListAsync();
        var grupos = await _db.Grupos.OrderBy(g => g.Nombre).ToListAsync();
        var areas = await _db.Areas.Where(a => a.Activo).OrderBy(a => a.Nombre).ToListAsync();
        return Ok(new { padres, grupos, areas });
    }
}
