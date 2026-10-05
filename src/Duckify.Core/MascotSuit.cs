namespace Duckify.Core;

/// <summary>
/// The duck suit the park mascot wears, as pieces of the game's own apparel tables. Each table is one
/// outfit slot for one sex: the male tables hold Mascot_Body, Mascot_Shoes and Mascot_Head, the female
/// ones Mascot_Body_F, Mascot_Shoes_F and Mascot_Head. The body is a whole suit in the lower-body slot,
/// so the game's mascot outfit leaves the top and glasses slots empty.
/// </summary>
public static class MascotSuit
{
    public const string PiecePrefix = "Mascot_";

    /// <summary>The name of the empty entry every apparel table starts with.</summary>
    public const string Empty = "None";

    /// <summary>
    /// Which entry of one slot's table a visitor in the duck suit wears: the mascot piece, or the empty
    /// entry when the slot has no piece. Null when the table has neither, so the slot is left as it is.
    /// Names are compared the way the game compares them, ordinal and case-sensitive.
    /// </summary>
    public static int? Pick(IReadOnlyList<string?> itemNames)
    {
        int? empty = null;
        for (var i = 0; i < itemNames.Count; i++)
        {
            if (IsPiece(itemNames[i])) return i;
            if (empty == null && itemNames[i] == Empty) empty = i;
        }
        return empty;
    }

    /// <summary>Index of the table's empty entry, or null when it has none.</summary>
    public static int? EmptyIndex(IReadOnlyList<string?> itemNames)
    {
        for (var i = 0; i < itemNames.Count; i++)
            if (itemNames[i] == Empty) return i;
        return null;
    }

    public static bool IsPiece(string? itemName) => itemName != null && itemName.StartsWith(PiecePrefix, StringComparison.Ordinal);
}
