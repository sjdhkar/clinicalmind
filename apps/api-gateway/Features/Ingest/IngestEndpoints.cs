using System.Net.Http.Json;

namespace ClinicalMind.Gateway.Features.Ingest;

public record IngestRequest(
    string PatientId, string EncounterId,
    string DocumentType, string Content,
    Dictionary<string, string>? Metadata);

public record IngestResponse(string JobId, string Status, string Message);

public static class IngestEndpoints
{
    public static IEndpointRouteBuilder MapIngestEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/ingest").WithTags("ingest");

        // FIX: explicit Task<IResult> return type on async lambda
        group.MapPost("", async Task<IResult> (
            IngestRequest req,
            IHttpClientFactory factory,
            CancellationToken ct) =>
        {
            using var http = factory.CreateClient();
            http.BaseAddress = new Uri("http://ai-orchestrator:8000");

            var response = await http.PostAsJsonAsync("/ingest", new
            {
                patient_id = req.PatientId,
                encounter_id = req.EncounterId,
                document_type = req.DocumentType,
                content = req.Content,
                metadata = req.Metadata ?? new Dictionary<string, string>(),
            }, ct);

            response.EnsureSuccessStatusCode();
            var result = await response.Content.ReadFromJsonAsync<IngestResponse>(ct);
            return Results.Ok(result);
        }).WithSummary("Ingest clinical document into RAG corpus");

        return app;
    }
}

public static class HealthEndpoints
{
    public static IEndpointRouteBuilder MapHealthCheck(this IEndpointRouteBuilder app)
    {
        app.MapGet("/health", () => Results.Ok(new
        {
            status = "ok",
            service = "clinicalmind-gateway",
            timestamp = DateTimeOffset.UtcNow,
        })).WithTags("health");
        return app;
    }
}
