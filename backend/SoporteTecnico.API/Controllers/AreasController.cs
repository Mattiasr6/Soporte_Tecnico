using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using SoporteTecnico.API.Data;

namespace SoporteTecnico.API.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class AreasController : ControllerBase
{
    private readonly AppDbContext _db;

    public AreasController(AppDbContext db)
    {
        _db = db;
    }

    [HttpGet]
    public async Task<ActionResult> Get()
    {
        var areas = await _db.Atenciones
            .Where(a => a.AreaSolicitante != null && a.AreaSolicitante.Trim() != "")
            .Select(a => a.AreaSolicitante)
            .Distinct()
            .OrderBy(a => a)
            .ToListAsync();

        var extraAreas = new[] { "Asistente F.C.S.", "ADI (Academia de Idiomas)", "Archivos Contabilidad", "Laboratorios y gabinetes de Medicina", "Plaza UPDS", "Vicerrectorado Administrativo", "Sala 2 (Directorio)", "Sala 3 (Directorio)" }
            .Concat(Enumerable.Range(1, 12).Select(i => $"Aula A-{i:D2}"))
            .Concat(Enumerable.Range(1, 21).Select(i => $"Aula B-{i:D2}"))
            .Concat(Enumerable.Range(1, 20).Select(i => $"Aula C-{i:D2}"))
            .Concat(Enumerable.Range(1, 18).Select(i => $"Aula D-{i:D2}"))
            .Concat(Enumerable.Range(1, 5).Select(i => $"Aula E-{i:D2}"))
            .ToArray();
        areas = areas.Union(extraAreas).OrderBy(a => a).ToList();
        if (areas.Count == 1) // solo Plaza UPDS, sin datos reales
        {
            areas = new List<string>
            {
                "Archivo", "Aula B-02", "Aula B-05 MED",
                "Aula B-06", "Aula B-10", "Aula B-11", "Aula C-04", "Aula C-07",
                "Aula C-09", "Aula C-12", "Biblioteca", "Bienestar Estudiantil",
                "Caja", "CAP", "Contabilidad", "Coordinación Acad. FCS",
                "Directorio", "EIAG", "Laboratorios de Computo", "Marketing",
                "Publicidad", "Recepción", "Rectorado", "Registro",
                "Relaciones Públicas", "Sala de Docentes", "Sala de lectura",
                "Sala Magna", "Secretaria General", "Sistemas",
                "Talento Humano", "Vicerrectorado",
            };
        }

        return Ok(areas);
    }
}
