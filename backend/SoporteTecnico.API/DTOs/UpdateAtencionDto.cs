namespace SoporteTecnico.API.DTOs;

public record UpdateAtencionDto
{
    public string? AreaSolicitante { get; init; }
    public string? MedioSolicitud { get; init; }
    public string? UsuarioSolicitante { get; init; }
    public string? Categoria { get; init; }
    public string? Descripcion { get; init; }
    public string? Solucion { get; init; }
    public string? Observaciones { get; init; }
    public string? EnlaceApoyo { get; init; }
}
