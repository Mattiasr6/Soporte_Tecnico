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

            entity.Property(u => u.MicrosoftId)
                  .IsRequired()
                  .HasMaxLength(255);

            entity.Property(u => u.Email)
                  .IsRequired()
                  .HasMaxLength(255);

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

            entity.Property(u => u.CreatedAt);

            entity.Property(u => u.UpdatedAt);

            entity.HasIndex(u => u.MicrosoftId).IsUnique();
            entity.HasIndex(u => u.Email).IsUnique();

            entity.HasData(
                new Usuario
                {
                    Id = 1,
                    MicrosoftId = "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    Email = "carlos@empresa.com",
                    DisplayName = "Carlos Méndez",
                    Role = "Jefe",
                    EstadoActual = false,
                    CreatedAt = new DateTime(2025, 1, 1, 0, 0, 0, DateTimeKind.Utc),
                    UpdatedAt = new DateTime(2025, 1, 1, 0, 0, 0, DateTimeKind.Utc)
                },
                new Usuario
                {
                    Id = 2,
                    MicrosoftId = "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    Email = "ana@empresa.com",
                    DisplayName = "Ana López",
                    Role = "Tecnico",
                    EstadoActual = false,
                    CreatedAt = new DateTime(2025, 1, 1, 0, 0, 0, DateTimeKind.Utc),
                    UpdatedAt = new DateTime(2025, 1, 1, 0, 0, 0, DateTimeKind.Utc)
                },
                new Usuario
                {
                    Id = 3,
                    MicrosoftId = "c3d4e5f6-a7b8-9012-cdef-123456789012",
                    Email = "pedro@empresa.com",
                    DisplayName = "Pedro Ramírez",
                    Role = "Tecnico",
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
