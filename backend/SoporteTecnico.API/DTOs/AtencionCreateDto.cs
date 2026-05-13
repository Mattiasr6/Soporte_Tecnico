namespace SoporteTecnico.API.DTOs;

public class AtencionCreateDto
{
    public string AreaSolicitante { get; set; } = string.Empty;
    public string Categoria { get; set; } = string.Empty;
    public string Descripcion { get; set; } = string.Empty;
    public string Solucion { get; set; } = string.Empty;
    public string? Observaciones { get; set; }
    public DateOnly FechaRegistro { get; set; } = DateOnly.FromDateTime(DateTime.UtcNow);
}
