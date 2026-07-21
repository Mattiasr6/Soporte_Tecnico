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

        areas = areas
            .Union(new[] { "Plaza UPDS", "Vicerrectorado Administrativo", "Sala 2 (Directorio)", "Sala 3 (Directorio)" })
            .OrderBy(a => a)
            .ToList();

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
