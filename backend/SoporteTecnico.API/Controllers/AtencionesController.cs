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

    private string? GetMicrosoftId() =>
        User.FindFirstValue("http://schemas.microsoft.com/identity/claims/objectidentifier")
        ?? User.FindFirstValue("oid");

    [HttpPost("batch")]
    public async Task<ActionResult> CreateBatch([FromBody] AtencionBulkCreateDto dto)
    {
        var msId = GetMicrosoftId();
        if (msId is null) return Unauthorized();

        var usuario = await _db.Usuarios.FirstOrDefaultAsync(u => u.MicrosoftId == msId);
        if (usuario is null) return NotFound("Usuario no registrado en el sistema.");

        if (dto.Atenciones.Count == 0)
            return BadRequest("La lista de atenciones está vacía.");

        var atenciones = dto.Atenciones.Select(a => new Atencion
        {
            UsuarioId = usuario.Id,
            AreaSolicitante = a.AreaSolicitante,
            Categoria = a.Categoria,
            Descripcion = a.Descripcion,
            Solucion = a.Solucion,
            Observaciones = a.Observaciones,
            FechaRegistro = a.FechaRegistro
        }).ToList();

        _db.Atenciones.AddRange(atenciones);
        await _db.SaveChangesAsync();

        return Ok(new { registrosInsertados = atenciones.Count });
    }
}
