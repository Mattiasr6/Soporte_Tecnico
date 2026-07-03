using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace SoporteTecnico.API.Migrations
{
    /// <inheritdoc />
    public partial class AddHorarios : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "Horarios",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    UsuarioId = table.Column<int>(type: "INTEGER", nullable: false),
                    Label = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    HoraInicio1 = table.Column<string>(type: "TEXT", maxLength: 5, nullable: true),
                    HoraFin1 = table.Column<string>(type: "TEXT", maxLength: 5, nullable: true),
                    HoraInicio2 = table.Column<string>(type: "TEXT", maxLength: 5, nullable: true),
                    HoraFin2 = table.Column<string>(type: "TEXT", maxLength: 5, nullable: true),
                    Mes = table.Column<int>(type: "INTEGER", nullable: false),
                    Anio = table.Column<int>(type: "INTEGER", nullable: false),
                    CreatedAt = table.Column<DateTime>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Horarios", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Horarios_Usuarios_UsuarioId",
                        column: x => x.UsuarioId,
                        principalTable: "Usuarios",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "IX_Horarios_UsuarioId_Mes_Anio",
                table: "Horarios",
                columns: new[] { "UsuarioId", "Mes", "Anio" },
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "Horarios");
        }
    }
}
