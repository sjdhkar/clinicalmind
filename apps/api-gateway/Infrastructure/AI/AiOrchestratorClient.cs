using ClinicalMind.Gateway.Features.Chat;
using System.Net.Http.Json;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;

namespace ClinicalMind.Gateway.Infrastructure.AI;

public interface IAiOrchestratorClient
{
    IAsyncEnumerable<string> StreamChatAsync(
        string query, string patientId, string encounterId,
        string userId, string traceId, CancellationToken cancellationToken);

    Task<ChatResult> ChatAsync(
        string query, string patientId, string encounterId,
        string userId, string traceId, CancellationToken cancellationToken);
}

public class AiOrchestratorClient(HttpClient http, ILogger<AiOrchestratorClient> logger)
    : IAiOrchestratorClient
{
    public async IAsyncEnumerable<string> StreamChatAsync(
        string query, string patientId, string encounterId,
        string userId, string traceId,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var payload = new
        {
            query,
            patient_id = patientId,
            encounter_id = encounterId,
            user_id = userId,
            stream = true,
        };

        var request = new HttpRequestMessage(HttpMethod.Post, "/chat/stream")
        {
            Content = new StringContent(
                JsonSerializer.Serialize(payload),
                Encoding.UTF8,
                "application/json"),
        };

        // ── FIX: cannot yield inside catch — capture error, yield after ──
        HttpResponseMessage? response = null;
        Exception? connectionError = null;

        try
        {
            response = await http.SendAsync(
                request,
                HttpCompletionOption.ResponseHeadersRead,
                cancellationToken);
            response.EnsureSuccessStatusCode();
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "[{TraceId}] AI orchestrator connection failed", traceId);
            connectionError = ex;
        }

        // Yield error outside catch block — C# language requirement
        if (connectionError != null)
        {
            yield return $"event: error\ndata: {{\"message\": \"AI service unavailable\"}}\n\n";
            yield break;
        }

        await using var stream = await response!.Content.ReadAsStreamAsync(cancellationToken);
        using var reader = new StreamReader(stream);

        while (!reader.EndOfStream && !cancellationToken.IsCancellationRequested)
        {
            var line = await reader.ReadLineAsync(cancellationToken);
            if (line is null) break;
            yield return line + "\n";
            if (line.Length == 0) yield return "\n";
        }
    }

    public async Task<ChatResult> ChatAsync(
        string query, string patientId, string encounterId,
        string userId, string traceId, CancellationToken cancellationToken)
    {
        var payload = new
        {
            query,
            patient_id = patientId,
            encounter_id = encounterId,
            user_id = userId,
            stream = false,
        };

        var response = await http.PostAsJsonAsync("/chat", payload, cancellationToken);
        response.EnsureSuccessStatusCode();

        var raw = await response.Content.ReadFromJsonAsync<OrchestratorChatResponse>(
            cancellationToken: cancellationToken);

        return new ChatResult(
            Answer: raw?.Answer ?? string.Empty,
            TraceId: traceId,
            ModelUsed: raw?.ModelUsed ?? "unknown",
            CitationCount: raw?.CitationCount ?? 0,
            InsufficientData: raw?.InsufficientData ?? false);
    }

    private record OrchestratorChatResponse(
        string Answer, string TraceId, string ModelUsed,
        int CitationCount, bool InsufficientData);
}
