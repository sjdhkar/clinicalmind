using ClinicalMind.Gateway.Domain.Audit;
using ClinicalMind.Gateway.Features.Chat;
using ClinicalMind.Gateway.Features.Ingest;
using ClinicalMind.Gateway.Infrastructure.AI;
using ClinicalMind.Gateway.Infrastructure.Redis;
using ClinicalMind.Gateway.Middleware;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using StackExchange.Redis;

var builder = WebApplication.CreateBuilder(args);

// ── Configuration ─────────────────────────────────────────────
var config = builder.Configuration;

// ── Authentication (Azure AD B2C) ─────────────────────────────
// Bypassed in dev when AuthBypassDev=true (see appsettings.Development.json)
if (!config.GetValue<bool>("Auth:BypassDev"))
{
    builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
        .AddJwtBearer(options =>
        {
            options.Authority = $"https://login.microsoftonline.com/{config["Auth:TenantId"]}/v2.0";
            options.Audience = config["Auth:ClientId"];
        });
    builder.Services.AddAuthorization();
}

// ── MediatR (CQRS) ────────────────────────────────────────────
builder.Services.AddMediatR(cfg =>
    cfg.RegisterServicesFromAssembly(typeof(Program).Assembly));

// ── Redis ────────────────────────────────────────────────────
builder.Services.AddSingleton<IConnectionMultiplexer>(sp =>
    ConnectionMultiplexer.Connect(config.GetConnectionString("Redis") ?? "localhost:6379"));
builder.Services.AddSingleton<IRateLimiter, RedisTokenBucketLimiter>();

// ── Database (audit log) ──────────────────────────────────────
builder.Services.AddDbContext<AuditDbContext>(options =>
    options.UseNpgsql(config.GetConnectionString("Default")));

// ── AI Orchestrator client ────────────────────────────────────
builder.Services.AddHttpClient<IAiOrchestratorClient, AiOrchestratorClient>(client =>
{
    client.BaseAddress = new Uri(config["AiOrchestrator:BaseUrl"] ?? "http://ai-orchestrator:8000");
    client.Timeout = TimeSpan.FromSeconds(120); // SSE streams can be long
});

// ── OpenTelemetry ─────────────────────────────────────────────
builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("clinicalmind-gateway"))
    .WithTracing(tracing => tracing
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddOtlpExporter(o => o.Endpoint = new Uri(
            config["Otel:Endpoint"] ?? "http://localhost:4317")));

// ── CORS (Angular dev server) ──────────────────────────────────
builder.Services.AddCors(options =>
    options.AddDefaultPolicy(policy => policy
        .WithOrigins("http://localhost:4200")
        .AllowAnyHeader()
        .AllowAnyMethod()
        .AllowCredentials())); // required for SSE

// ── Scalar API docs ───────────────────────────────────────────
builder.Services.AddEndpointsApiExplorer();

var app = builder.Build();

// ── Middleware pipeline ────────────────────────────────────────
app.UseCors();
app.UseMiddleware<AuditLoggingMiddleware>();
app.UseMiddleware<RateLimitingMiddleware>();

if (!config.GetValue<bool>("Auth:BypassDev"))
{
    app.UseAuthentication();
    app.UseAuthorization();
}

// ── API docs ──────────────────────────────────────────────────
if (app.Environment.IsDevelopment())
{
    app.MapScalarApiReference();
}

// ── Endpoints ─────────────────────────────────────────────────
app.MapHealthCheck();
app.MapChatEndpoints();
app.MapIngestEndpoints();

// ── DB migrations ─────────────────────────────────────────────
if (app.Environment.IsDevelopment())
{
    using var scope = app.Services.CreateScope();
    var db = scope.ServiceProvider.GetRequiredService<AuditDbContext>();
    await db.Database.EnsureCreatedAsync();
}

await app.RunAsync();
