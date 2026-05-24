using StackExchange.Redis;

namespace ClinicalMind.Gateway.Infrastructure.Redis;

public interface IRateLimiter
{
    Task<RateLimitResult> CheckAsync(string userId, RateLimitTier tier);
}

public record RateLimitResult(bool Allowed, int Remaining, DateTimeOffset Reset);

public enum RateLimitTier
{
    Standard = 20,   // calls/minute for regular users
    Admin = 100,     // calls/minute for admin users
    Background = 0,  // unlimited for background jobs
}

/// <summary>
/// Redis-backed token bucket rate limiter.
/// Uses a Lua script for atomic check-and-decrement.
/// </summary>
public class RedisTokenBucketLimiter(IConnectionMultiplexer redis, IConfiguration config)
    : IRateLimiter
{
    private static readonly string _luaScript = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local now = tonumber(ARGV[2])
        local window = tonumber(ARGV[3])

        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now

        -- Refill tokens based on time elapsed
        local elapsed = now - last_refill
        local refill = math.floor(elapsed / window * capacity)
        tokens = math.min(capacity, tokens + refill)

        local allowed = 0
        if tokens >= 1 then
            tokens = tokens - 1
            allowed = 1
        end

        redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
        redis.call('EXPIRE', key, window * 2)

        return {allowed, tokens}
        """;

    private readonly IDatabase _db = redis.GetDatabase();

    public async Task<RateLimitResult> CheckAsync(string userId, RateLimitTier tier)
    {
        if (tier == RateLimitTier.Background)
            return new RateLimitResult(true, int.MaxValue, DateTimeOffset.UtcNow.AddMinutes(1));

        int capacity = (int)tier;
        var key = $"ratelimit:{userId}";
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        var windowSeconds = 60;

        try
        {
            var result = await _db.ScriptEvaluateAsync(
                _luaScript,
                keys: [new RedisKey(key)],
                values: [capacity, now, windowSeconds]);

            var arr = (RedisResult[])result!;
            var allowed = (int)arr[0] == 1;
            var remaining = (int)arr[1];
            var reset = DateTimeOffset.UtcNow.AddSeconds(windowSeconds);

            return new RateLimitResult(allowed, remaining, reset);
        }
        catch
        {
            // If Redis is down, fail open (don't block users)
            return new RateLimitResult(true, capacity, DateTimeOffset.UtcNow.AddMinutes(1));
        }
    }
}
