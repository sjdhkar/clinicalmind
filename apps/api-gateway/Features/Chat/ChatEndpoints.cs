using ClinicalMind.Gateway.Infrastructure.AI;
using MediatR;
using System.Runtime.CompilerServices;

namespace ClinicalMind.Gateway.Features.Chat;

// ── Request / Response contracts ─────────────────────────────────

public record ChatStreamRequest(
    string Query,
    string PatientId,
    string EncounterId
);

public record ChatRequest(
    string Query,
    string PatientId,
    string EncounterId
);

// ── MediatR commands ─────────────────────────────────────────────

public record StreamChatCommand(
    string Query,
    string PatientId,
    string EncounterId,
    string UserId,
    string TraceId
) : IStreamRequest<string>;

public record ChatCommand(
    string Query,
    string PatientId,
    string EncounterId,
    string UserId,
    string TraceId
) : IRequest<ChatResult>;

public record ChatResult(
    string Answer,
    string TraceId,
    string ModelUsed,
    int CitationCount,
    bool InsufficientData
);

// ── Stream handler ────────────────────────────────────────────────

public class StreamChatHandler(IAiOrchestratorClient orchestrator)
    : IStreamRequestHandler<StreamChatCommand, string>
{
    public async IAsyncEnumerable<string> Handle(
        StreamChatCommand request,
        [EnumeratorCancellation] CancellationToken ct)
    {
        await foreach (var chunk in orchestrator.StreamChatAsync(
            query: request.Query,
            patientId: request.PatientId,
            encounterId: request.EncounterId,
            userId: request.UserId,
            traceId: request.TraceId,
            cancellationToken: ct))
        {
            yield return chunk;
        }
    }
}

// ── Non-stream handler ────────────────────────────────────────────

public class ChatHandler(IAiOrchestratorClient orchestrator)
    : IRequestHandler<ChatCommand, ChatResult>
{
    public async Task<ChatResult> Handle(ChatCommand request, CancellationToken ct)
        => await orchestrator.ChatAsync(
            query: request.Query,
            patientId: request.PatientId,
            encounterId: request.EncounterId,
            userId: request.UserId,
            traceId: request.TraceId,
            cancellationToken: ct);
}

// ── Endpoint registration ─────────────────────────────────────────

public static class ChatEndpoints
{
    public static IEndpointRouteBuilder MapChatEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/chat")
            .WithTags("chat")
            .WithOpenApi();

        // SSE streaming endpoint
        group.MapPost("/stream", async (
            HttpContext ctx,
            ChatStreamRequest req,
            IMediator mediator,
            CancellationToken ct) =>
        {
            var userId = ctx.User?.Identity?.Name ?? "anonymous";
            var traceId = ctx.TraceIdentifier;

            ctx.Response.Headers.Append("Content-Type", "text/event-stream");
            ctx.Response.Headers.Append("Cache-Control", "no-cache");
            ctx.Response.Headers.Append("X-Accel-Buffering", "no"); // disable nginx buffering

            var command = new StreamChatCommand(
                req.Query, req.PatientId, req.EncounterId, userId, traceId);

            await foreach (var chunk in mediator.CreateStream(command, ct))
            {
                // Forward SSE events from the AI orchestrator to the client
                await ctx.Response.WriteAsync(chunk, ct);
                await ctx.Response.Body.FlushAsync(ct);
            }
        })
        .WithSummary("Stream clinical AI response via SSE")
        .WithDescription(
            "Connects to the AI orchestrator SSE stream and proxies it to the Angular client. " +
            "Events: token | citation | metadata | done | error");

        // Non-streaming endpoint (for eval pipeline + programmatic access)
        group.MapPost("", async (
            ChatRequest req,
            IMediator mediator,
            HttpContext ctx,
            CancellationToken ct) =>
        {
            var userId = ctx.User?.Identity?.Name ?? "anonymous";
            var traceId = ctx.TraceIdentifier;

            var result = await mediator.Send(
                new ChatCommand(req.Query, req.PatientId, req.EncounterId, userId, traceId), ct);

            return Results.Ok(result);
        })
        .WithSummary("Non-streaming clinical AI response")
        .Produces<ChatResult>();

        return app;
    }
}
