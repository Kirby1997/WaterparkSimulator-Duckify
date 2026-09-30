namespace Duckify.Core;

/// <summary>The duck a character is drawn as. <see cref="Random"/> is only a setting, never a result.</summary>
public enum DuckStyle
{
    Random,
    Classic,
    Mallard,
    Rubber,
}

/// <summary>Which game skeleton a duck was built on.</summary>
public enum DuckSex
{
    Male,
    Female,
}

/// <summary>The third-person body, or the first-person wings that replace the player's arms.</summary>
public enum DuckPart
{
    Body,
    Wings,
}

public static class DuckNames
{
    /// <summary>File and embedded resource name of one duck mesh, e.g. "classic_female_wings.duckmesh".</summary>
    public static string FileName(DuckStyle style, DuckSex sex, DuckPart part)
    {
        if (style == DuckStyle.Random) throw new ArgumentException("Random is a setting, not a duck.", nameof(style));
        return $"{Lower(style)}_{Lower(sex)}_{Lower(part)}.duckmesh";
    }

    /// <summary>The game's female meshes carry "Female" in their name (CC_Body_Female_LOD0, First_Person_Female).</summary>
    public static DuckSex SexFromMeshName(string? meshName) =>
        meshName != null && meshName.Contains("Female", StringComparison.OrdinalIgnoreCase) ? DuckSex.Female : DuckSex.Male;

    private static string Lower<T>(T value) where T : Enum => value.ToString().ToLowerInvariant();
}
