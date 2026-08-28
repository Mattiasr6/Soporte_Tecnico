namespace SoporteTecnico.API.Models;

public class Area
{
    public int Id { get; set; }
    public int GrupoPadreId { get; set; }
    public int? GrupoId { get; set; }
    public string Nombre { get; set; } = string.Empty;
    public bool Activo { get; set; } = true;

    public GrupoPadre GrupoPadre { get; set; } = null!;
    public Grupo? Grupo { get; set; }
}
