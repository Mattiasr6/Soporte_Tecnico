using SoporteTecnico.API.Models;

namespace SoporteTecnico.API.Services;

public static class HorarioHelper
{
    private static readonly TimeZoneInfo BoliviaTz = TimeZoneInfo.FindSystemTimeZoneById("America/La_Paz");

    /// <summary>
    /// Devuelve el estado efectivo considerando si el usuario está dentro de su horario.
    /// Si está Disponible u Ocupado pero fuera de su horario registrado → Extraturno.
    /// </summary>
    public static string EstadoEfectivo(EstadoUsuario estadoActual, Horario? horario)
    {
        // Ausente se queda igual (desconectado)
        if (estadoActual == EstadoUsuario.Ausente)
            return "ausente";

        // Extraturno se queda igual
        if (estadoActual == EstadoUsuario.Extraturno)
            return "extraturno";

        // Si está disponible/ocupado, verificar horario
        if (estadoActual is EstadoUsuario.Disponible or EstadoUsuario.Ocupado)
        {
            if (!EstaEnHorario(horario))
                return "extraturno";
        }

        return estadoActual.ToString().ToLower();
    }

    private static bool EstaEnHorario(Horario? horario)
    {
        if (horario is null)
            return true; // sin horario definido → no se puede determinar

        var now = TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, BoliviaTz).TimeOfDay;

        if (TimeSpan.TryParse(horario.HoraInicio1, out var ini1) &&
            TimeSpan.TryParse(horario.HoraFin1, out var fin1) &&
            now >= ini1 && now <= fin1)
            return true;

        if (TimeSpan.TryParse(horario.HoraInicio2, out var ini2) &&
            TimeSpan.TryParse(horario.HoraFin2, out var fin2) &&
            now >= ini2 && now <= fin2)
            return true;

        return false;
    }
}
