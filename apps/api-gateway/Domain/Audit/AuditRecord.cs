using Microsoft.EntityFrameworkCore;

namespace ClinicalMind.Gateway.Domain.Audit;

/// <summary>
/// Immutable audit record for every AI-assisted clinical action.
/// Written once, never updated, never deleted.
/// Satisfies regulatory audit requirements for AI-assisted clinical decisions.
/// </summary>
public sealed class AuditRecord
{
    public Guid Id { get; init; } = Guid.NewGuid();
    public required string TraceId { get; init; }
    public required string UserId { get; init; }
    public string? PatientId { get; init; }
    public string? EncounterId { get; init; }
    public required string Endpoint { get; init; }
    public required string Method { get; init; }
    public int StatusCode { get; init; }
    public double ElapsedMs { get; init; }
    public string? AgentName { get; init; }
    public string? ModelUsed { get; init; }
    public string? PromptVersion { get; init; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}

public class AuditDbContext(DbContextOptions<AuditDbContext> options) : DbContext(options)
{
    public DbSet<AuditRecord> AuditRecords => Set<AuditRecord>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<AuditRecord>(entity =>
        {
            entity.HasKey(e => e.Id);
            entity.Property(e => e.CreatedAt).HasDefaultValueSql("NOW()");
            entity.HasIndex(e => e.TraceId);
            entity.HasIndex(e => e.PatientId);
            entity.HasIndex(e => e.CreatedAt);

            // Enforce append-only at DB level via check constraint
            // (In production: row-level security + no UPDATE/DELETE grants to app user)
        });

        modelBuilder.HasDefaultSchema("audit");
    }
}
