using System.Text.Json.Serialization;

namespace SoporteTecnico.API.Models;

public class Grupo
{
    public int Id { get; set; }
    public int GrupoPadreId { get; set; }
    public string Nombre { get; set; } = string.Empty;
    public bool Activo { get; set; } = true;

    [JsonIgnore]
    public GrupoPadre GrupoPadre { get; set; } = null!;

    [JsonIgnore]
    public ICollection<Area> Areas { get; set; } = new List<Area>();
}
