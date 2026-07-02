using System.Collections.Concurrent;

namespace SoporteTecnico.API.Services;

public class InMemoryVerificationCodeStore : IVerificationCodeStore
{
    private static readonly ConcurrentDictionary<string, CodeEntry> _codes = new();
    private static readonly TimeSpan Expiration = TimeSpan.FromMinutes(5);

    public void Store(string email, string code)
    {
        var normalized = NormalizeEmail(email);
        Remove(normalized);
        _codes[normalized] = new CodeEntry(code, DateTime.UtcNow + Expiration);
    }

    public string? Get(string email)
    {
        var normalized = NormalizeEmail(email);
        if (_codes.TryGetValue(normalized, out var entry))
        {
            if (entry.ExpiresAt > DateTime.UtcNow)
                return entry.Code;

            Remove(normalized);
        }
        return null;
    }

    public void Remove(string email)
    {
        var normalized = NormalizeEmail(email);
        _codes.TryRemove(normalized, out _);
    }

    private static string NormalizeEmail(string email) =>
        email.Trim().ToLowerInvariant();

    private record CodeEntry(string Code, DateTime ExpiresAt);
}
