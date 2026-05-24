FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY ClinicalMind.Gateway.csproj .
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /app/publish --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
LABEL maintainer="Srujan Dharkar <github.com/sjdhkar>"
WORKDIR /app
RUN addgroup --system clinicalmind && adduser --system --ingroup clinicalmind clinicalmind
COPY --from=build /app/publish .
RUN chown -R clinicalmind:clinicalmind /app
USER clinicalmind
ENV ASPNETCORE_URLS=http://+:8080
ENV ASPNETCORE_ENVIRONMENT=Production
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
ENTRYPOINT ["dotnet", "ClinicalMind.Gateway.dll"]
