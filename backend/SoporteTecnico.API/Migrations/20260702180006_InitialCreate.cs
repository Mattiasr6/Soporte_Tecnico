using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace SoporteTecnico.API.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "Usuarios",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Email = table.Column<string>(type: "TEXT", maxLength: 255, nullable: false),
                    PasswordHash = table.Column<string>(type: "TEXT", nullable: true),
                    DisplayName = table.Column<string>(type: "TEXT", maxLength: 255, nullable: false),
                    Role = table.Column<string>(type: "TEXT", maxLength: 50, nullable: false, defaultValue: "Tecnico"),
                    EstadoActual = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    CanViewDashboard = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    CreatedAt = table.Column<DateTime>(type: "TEXT", nullable: false),
                    UpdatedAt = table.Column<DateTime>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Usuarios", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "Atenciones",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    UsuarioId = table.Column<int>(type: "INTEGER", nullable: false),
                    AreaSolicitante = table.Column<string>(type: "TEXT", maxLength: 200, nullable: false),
                    MedioSolicitud = table.Column<string>(type: "TEXT", maxLength: 50, nullable: false),
                    UsuarioSolicitante = table.Column<string>(type: "TEXT", maxLength: 10, nullable: false),
                    Categoria = table.Column<string>(type: "TEXT", maxLength: 200, nullable: false),
                    Descripcion = table.Column<string>(type: "TEXT", maxLength: 1000, nullable: false),
                    Solucion = table.Column<string>(type: "TEXT", maxLength: 1000, nullable: false),
                    Observaciones = table.Column<string>(type: "TEXT", maxLength: 2000, nullable: true),
                    EnlaceApoyo = table.Column<string>(type: "TEXT", maxLength: 500, nullable: true),
                    FechaRegistro = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Atenciones", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Atenciones_Usuarios_UsuarioId",
                        column: x => x.UsuarioId,
                        principalTable: "Usuarios",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.InsertData(
                table: "Usuarios",
                columns: new[] { "Id", "CreatedAt", "DisplayName", "Email", "PasswordHash", "Role", "UpdatedAt" },
                values: new object[] { 1, new DateTime(2025, 1, 1, 0, 0, 0, 0, DateTimeKind.Utc), "Mattias Ribera", "riberarojasmattias6@gmail.com", null, "Jefe", new DateTime(2025, 1, 1, 0, 0, 0, 0, DateTimeKind.Utc) });

            migrationBuilder.CreateIndex(
                name: "IX_Atenciones_FechaRegistro",
                table: "Atenciones",
                column: "FechaRegistro");

            migrationBuilder.CreateIndex(
                name: "IX_Atenciones_UsuarioId",
                table: "Atenciones",
                column: "UsuarioId");

            migrationBuilder.CreateIndex(
                name: "IX_Usuarios_Email",
                table: "Usuarios",
                column: "Email",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "Atenciones");

            migrationBuilder.DropTable(
                name: "Usuarios");
        }
    }
}
