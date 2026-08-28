namespace SoporteTecnico.API.DTOs;

public class AtencionCreateDto
{
    public string AreaSolicitante { get; set; } = string.Empty;
    public int? GrupoPadreId { get; set; }
    public int? GrupoId { get; set; }
    public int? AreaId { get; set; }
    public string MedioSolicitud { get; set; } = string.Empty;
    public string UsuarioSolicitante { get; set; } = string.Empty;
    public string Categoria { get; set; } = string.Empty;
    public string Descripcion { get; set; } = string.Empty;
    public string Solucion { get; set; } = string.Empty;
    public string? Observaciones { get; set; }
    public string? EnlaceApoyo { get; set; }
    public int? ColaboradorId { get; set; }
    public DateOnly FechaRegistro { get; set; } = DateOnly.FromDateTime(DateTime.UtcNow);
}
