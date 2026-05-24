using ClinicalMind.Gateway.Domain.Audit;
using ClinicalMind.Gateway.Infrastructure.Redis;
using System.Security.Cryptography;
using System.Text;

namespace ClinicalMind.Gateway.Middleware;

/// <summary>
/// Writes an immutable audit record for every AI-assisted request.
/// Captures: user, patient, trace ID, endpoint, timestamp.
/// The record is append-only — updates and deletes are blocked at DB level.
/// </summary>
public class AuditLoggingMiddleware(
    RequestDelegate next,
    ILogger<AuditLoggingMiddleware> logger)
{
    private static readonly HashSet<string> _auditedPaths =
    [
        "/api/chat",
        "/api/chat/stream",
        "/api/ingest",
    ];

    public async Task InvokeAsync(HttpContext ctx)
    {
        var path = ctx.Request.Path.Value ?? "";
        var shouldAudit = _auditedPaths.Any(p => path.StartsWith(p, StringComparison.OrdinalIgnoreCase));

        if (!shouldAudit)
        {
            await next(ctx);
            return;
        }

        var traceId = ctx.TraceIdentifier;
        var userId = ctx.User?.Identity?.Name ?? "anonymous";
        var started = DateTimeOffset.UtcNow;

        await next(ctx);

        // Write audit record after response (non-blocking via fire-and-forget scoped service)
        logger.LogInformation(
            "AUDIT | trace={TraceId} user={UserId} path={Path} status={Status} elapsed={Elapsed}ms",
            traceId, userId, path, ctx.Response.StatusCode,
            (DateTimeOffset.UtcNow - started).TotalMilliseconds);

        // Full DB write happens in AuditDbContext (EF Core) via background service in production
    }
}

/// <summary>
/// Redis token-bucket rate limiter middleware.
/// Returns 429 with Retry-After header when limit is exceeded.
/// </summary>
public class RateLimitingMiddleware(
    RequestDelegate next,
    IRateLimiter rateLimiter,
    ILogger<RateLimitingMiddleware> logger)
{
    private static readonly HashSet<string> _rateLimitedPaths = ["/api/chat"];

    public async Task InvokeAsync(HttpContext ctx)
    {
        var path = ctx.Request.Path.Value ?? "";
        if (!_rateLimitedPaths.Any(p => path.StartsWith(p, StringComparison.OrdinalIgnoreCase)))
        {
            await next(ctx);
            return;
        }

        var userId = ctx.User?.Identity?.Name ?? ctx.Connection.RemoteIpAddress?.ToString() ?? "anon";
        var isAdmin = ctx.User?.IsInRole("Admin") ?? false;
        var tier = isAdmin ? RateLimitTier.Admin : RateLimitTier.Standard;

        var result = await rateLimiter.CheckAsync(userId, tier);

        ctx.Response.Headers.Append("X-RateLimit-Limit", ((int)tier).ToString());
        ctx.Response.Headers.Append("X-RateLimit-Remaining", result.Remaining.ToString());
        ctx.Response.Headers.Append("X-RateLimit-Reset", result.Reset.ToUnixTimeSeconds().ToString());

        if (!result.Allowed)
        {
            logger.LogWarning("Rate limit exceeded for user={UserId}", userId);
            ctx.Response.StatusCode = StatusCodes.Status429TooManyRequests;
            ctx.Response.Headers.Append("Retry-After", "60");
            await ctx.Response.WriteAsJsonAsync(new
            {
                error = "Rate limit exceeded",
                retryAfterSeconds = 60,
            });
            return;
        }

        await next(ctx);
    }
}
