using Microsoft.EntityFrameworkCore;
using SoporteTecnico.API.Models;

namespace SoporteTecnico.API.Data;

public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<Usuario> Usuarios => Set<Usuario>();
    public DbSet<Atencion> Atenciones => Set<Atencion>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Usuario>(entity =>
        {
            entity.ToTable("Usuarios");

            entity.Property(u => u.Email)
                  .IsRequired()
                  .HasMaxLength(255);

            entity.Property(u => u.PasswordHash)
                  .IsRequired(false);

            entity.Property(u => u.DisplayName)
                  .IsRequired()
                  .HasMaxLength(255);

            entity.Property(u => u.Role)
                  .IsRequired()
                  .HasMaxLength(50)
                  .HasDefaultValue("Tecnico");

            entity.Property(u => u.EstadoActual)
                  .IsRequired()
                  .HasDefaultValue(false);

            entity.Property(u => u.CanViewDashboard)
                  .HasDefaultValue(false);

            entity.HasIndex(u => u.Email).IsUnique();

            entity.HasData(
                new Usuario
                {
                    Id = 1,
                    Email = "riberarojasmattias6@gmail.com",
                    DisplayName = "Mattias Ribera",
                    Role = "Jefe",
                    EstadoActual = false,
                    CreatedAt = new DateTime(2025, 1, 1, 0, 0, 0, DateTimeKind.Utc),
                    UpdatedAt = new DateTime(2025, 1, 1, 0, 0, 0, DateTimeKind.Utc)
                }
            );
        });

        modelBuilder.Entity<Atencion>(entity =>
        {
            entity.ToTable("Atenciones");

            entity.Property(a => a.AreaSolicitante)
                  .IsRequired()
                  .HasMaxLength(200);

            entity.Property(a => a.MedioSolicitud)
                  .IsRequired()
                  .HasMaxLength(50);

            entity.Property(a => a.UsuarioSolicitante)
                  .IsRequired()
                  .HasMaxLength(10);

            entity.Property(a => a.Categoria)
                  .IsRequired()
                  .HasMaxLength(200);

            entity.Property(a => a.Descripcion)
                  .IsRequired()
                  .HasMaxLength(1000);

            entity.Property(a => a.Solucion)
                  .IsRequired()
                  .HasMaxLength(1000);

            entity.Property(a => a.Observaciones)
                  .HasMaxLength(2000);

            entity.Property(a => a.EnlaceApoyo)
                  .HasMaxLength(500);

            entity.Property(a => a.FechaRegistro)
                  .IsRequired();

            entity.Property(a => a.CreatedAt);

            entity.HasOne(a => a.Usuario)
                  .WithMany(u => u.Atenciones)
                  .HasForeignKey(a => a.UsuarioId)
                  .OnDelete(DeleteBehavior.Restrict);

            entity.HasIndex(a => a.UsuarioId);
            entity.HasIndex(a => a.FechaRegistro);
        });
    }
}
