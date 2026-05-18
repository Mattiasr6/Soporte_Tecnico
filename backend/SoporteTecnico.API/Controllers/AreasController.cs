using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace SoporteTecnico.API.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class AreasController : ControllerBase
{
    private static readonly string[] Areas =
    [
        "Acreditación Vicerrectorado",
        "Archivo",
        "Aula B-02 (antes RRPP)",
        "Aula B-02 Medicina",
        "Aula B-04 Medicina",
        "Aula B-05 Medicina",
        "Aula B-05 (Medicina)",
        "Aula B-06",
        "Aula B-06 Medicina",
        "Aula B-07 Medicina",
        "Aula B-10",
        "Aula B-11",
        "Aula C-04",
        "Aula C-07",
        "Aula C-09",
        "Aula C-12",
        "Aula D-01 Medicina",
        "B-05 Medicina",
        "Biblioteca",
        "Bienestar Estudiantil",
        "Caja",
        "CAP",
        "Centro de Inv. de Ciencias Empresariales",
        "Centro de Inv. de Ingeniería",
        "Centro de Inv. Facultad de Ingeniería",
        "Centro de investigación -Ingeniería",
        "Contabilidad",
        "Coordinación Acad. FCS",
        "Coordinacion Acad. Medicina",
        "Directorio",
        "EIAG",
        "Jefe de Carrera de Medicina",
        "Laboratorios de Computo",
        "Marketing",
        "Publicidad",
        "Recepción",
        "Rectorado",
        "Registro",
        "Relaciones Públicas",
        "Sala de Docentes",
        "Sala de lectura",
        "Sala Magna",
        "Secretaria General",
        "Sistemas",
        "Talentos Humanos",
        "Vicerrectorado"
    ];

    [HttpGet]
    public ActionResult Get()
    {
        return Ok(Areas);
    }
}
