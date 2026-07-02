FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY SoporteTecnico.API.csproj .
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /app

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
WORKDIR /app
COPY --from=build /app .
RUN mkdir -p /data && chown app:app /data
EXPOSE 5000
USER app
ENV ConnectionStrings__DefaultConnection="Data Source=/data/soporte.db"
ENTRYPOINT ["dotnet", "SoporteTecnico.API.dll"]
