namespace Duckify.Core;

/// <summary>The config values, read once per frame so one pass sees one consistent set.</summary>
public readonly record struct DuckSettings(bool Enabled, DuckStyle Style, bool ShowClothes);
