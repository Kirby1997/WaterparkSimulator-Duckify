namespace Duckify.Tests;

public class MascotSuitTests
{
    // Trimmed copies of the game's apparel tables (resources.assets). Index 0 is always "None".
    private static readonly string[] LowerBodyMale = { "None", "LowerBody_Default", "Jeans_01_Blue", "Overalls", "Mascot_Body" };
    private static readonly string[] LowerBodyFemale = { "None", "LowerBody_Default", "Yoga Pants", "Mascot_Body_F" };
    private static readonly string[] HatsFemale = { "None", "Mafia_Hat", "Mascot_Head", "Santa_Hood_F", "Duck_Helmet_F" };
    private static readonly string[] UpperBodyMale = { "None", "UpperBody_Default", "Hoodie_01" };

    [Fact]
    public void Slot_with_a_mascot_piece_wears_it()
    {
        Assert.Equal(4, MascotSuit.Pick(LowerBodyMale));
        Assert.Equal(3, MascotSuit.Pick(LowerBodyFemale));
        Assert.Equal(2, MascotSuit.Pick(HatsFemale));
    }

    [Fact]
    public void Slot_without_a_mascot_piece_is_emptied()
    {
        // The game's mascot outfit leaves the top and the glasses slot empty: the suit covers them.
        Assert.Equal(0, MascotSuit.Pick(UpperBodyMale));
        Assert.Equal(1, MascotSuit.Pick(new[] { "Cap", "None" }));
    }

    [Fact]
    public void Slot_with_neither_is_left_alone()
    {
        Assert.Null(MascotSuit.Pick(new[] { "Cap", "Visor" }));
        Assert.Null(MascotSuit.Pick(Array.Empty<string>()));
    }

    [Fact]
    public void Missing_names_are_skipped()
    {
        Assert.Equal(2, MascotSuit.Pick(new string?[] { null, "None", "Mascot_Shoes" }));
        Assert.Equal(1, MascotSuit.Pick(new string?[] { null, "None" }));
    }

    [Fact]
    public void Match_is_case_sensitive_like_the_game()
    {
        // The game compares apparel names with ordinal string equality.
        Assert.Null(MascotSuit.Pick(new[] { "mascot_head", "none" }));
    }

    [Theory]
    [InlineData("Mascot_Body", true)]
    [InlineData("Mascot_Shoes_F", true)]
    [InlineData("None", false)]
    [InlineData("Duck_Helmet_M", false)]
    [InlineData(null, false)]
    public void Recognises_mascot_pieces(string? name, bool expected) => Assert.Equal(expected, MascotSuit.IsPiece(name));

    [Fact]
    public void Finds_the_empty_entry()
    {
        Assert.Equal(0, MascotSuit.EmptyIndex(LowerBodyMale));
        Assert.Equal(1, MascotSuit.EmptyIndex(new string?[] { null, "None", "None" }));
        Assert.Null(MascotSuit.EmptyIndex(new[] { "Cap", "Visor" }));
    }
}
