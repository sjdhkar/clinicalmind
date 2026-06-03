using ClinicalMind.Gateway.Infrastructure.AI;
using MediatR;
using System.Runtime.CompilerServices;

namespace ClinicalMind.Gateway.Features.Chat;

// ── Request / Response contracts ──────────────────────────────────
public record ChatStreamRequest(string Query, string PatientId, string EncounterId);
public record ChatRequest(string Query, string PatientId, string EncounterId);

// ── MediatR commands ──────────────────────────────────────────────
public record StreamChatCommand(
    string Query, string PatientId, string EncounterId,
    string UserId, string TraceId
) : IStreamRequest<string>;

public record ChatCommand(
    string Query, string PatientId, string EncounterId,
    string UserId, string TraceId
) : IRequest<ChatResult>;

public record ChatResult(
    string Answer, string TraceId, string ModelUsed,
    int CitationCount, bool InsufficientData);

// ── Handlers ──────────────────────────────────────────────────────
public class StreamChatHandler(IAiOrchestratorClient orchestrator)
    : IStreamRequestHandler<StreamChatCommand, string>
{
    public async IAsyncEnumerable<string> Handle(
        StreamChatCommand request,
        [EnumeratorCancellation] CancellationToken ct)
    {
        await foreach (var chunk in orchestrator.StreamChatAsync(
            request.Query, request.PatientId, request.EncounterId,
            request.UserId, request.TraceId, ct))
        {
            yield return chunk;
        }
    }
}

public class ChatHandler(IAiOrchestratorClient orchestrator)
    : IRequestHandler<ChatCommand, ChatResult>
{
    public Task<ChatResult> Handle(ChatCommand request, CancellationToken ct)
        => orchestrator.ChatAsync(
            request.Query, request.PatientId, request.EncounterId,
            request.UserId, request.TraceId, ct);
}

// ── Endpoint registration ─────────────────────────────────────────
public static class ChatEndpoints
{
    public static IEndpointRouteBuilder MapChatEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/chat").WithTags("chat");

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
            ctx.Response.Headers.Append("X-Accel-Buffering", "no");

            var command = new StreamChatCommand(
                req.Query, req.PatientId, req.EncounterId, userId, traceId);

            await foreach (var chunk in mediator.CreateStream(command, ct))
            {
                await ctx.Response.WriteAsync(chunk, ct);
                await ctx.Response.Body.FlushAsync(ct);
            }
        }).WithSummary("Stream clinical AI response via SSE");

        // Non-streaming — FIX: explicit Task<IResult> return type
        group.MapPost("", async Task<IResult> (
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
        }).WithSummary("Non-streaming clinical AI response");

        return app;
    }
}
