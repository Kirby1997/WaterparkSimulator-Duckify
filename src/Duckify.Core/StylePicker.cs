namespace Duckify.Core;

public static class StylePicker
{
    public static IReadOnlyList<DuckStyle> Concrete { get; } = new[] { DuckStyle.Classic, DuckStyle.Mallard, DuckStyle.Rubber };

    /// <summary>
    /// The duck to draw for one character. A fixed setting is used for everyone. Random picks from
    /// <paramref name="available"/> by a stable hash of the name, so a character keeps the same duck
    /// across reloads and on every player's screen.
    /// </summary>
    public static DuckStyle Pick(DuckStyle setting, string? characterName, IReadOnlyList<DuckStyle>? available = null)
    {
        var pool = available ?? Concrete;
        if (pool.Count == 0) throw new ArgumentException("No duck styles are available.", nameof(available));
        if (setting != DuckStyle.Random) return pool.Contains(setting) ? setting : pool[0];
        if (string.IsNullOrEmpty(characterName)) return pool[0];
        return pool[(int)(Fnv1a(characterName) % (uint)pool.Count)];
    }

    /// <summary>32-bit FNV-1a over the name's UTF-16 code units. Unlike string.GetHashCode it is the same on every run.</summary>
    public static uint Fnv1a(string text)
    {
        var hash = 2166136261u;
        foreach (var c in text)
        {
            hash ^= c;
            hash *= 16777619u;
        }
        return hash;
    }
}
