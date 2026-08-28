namespace SoporteTecnico.API.Models;

public class Atencion
{
    public int Id { get; set; }
    public int UsuarioId { get; set; }
    public int? GrupoPadreId { get; set; }
    public int? GrupoId { get; set; }
    public int? AreaId { get; set; }
    public string AreaSolicitante { get; set; } = string.Empty; // Legacy varchar, mantener para histórico
    public string MedioSolicitud { get; set; } = string.Empty;
    public string UsuarioSolicitante { get; set; } = string.Empty;
    public string Categoria { get; set; } = string.Empty;
    public string Descripcion { get; set; } = string.Empty;
    public string Solucion { get; set; } = string.Empty;
    public string? Observaciones { get; set; }
    public string? EnlaceApoyo { get; set; }
    public int? ColaboradorId { get; set; }
    public bool FueraDeTurno { get; set; } = false;
    public DateOnly FechaRegistro { get; set; } = DateOnly.FromDateTime(DateTime.UtcNow);
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public Usuario Usuario { get; set; } = null!;
    public Usuario? Colaborador { get; set; }
    public GrupoPadre? GrupoPadre { get; set; }
    public Grupo? Grupo { get; set; }
    public Area? Area { get; set; }
}
