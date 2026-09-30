namespace Duckify.Tests;

public class StylePickerTests
{
    [Theory]
    [InlineData(DuckStyle.Classic)]
    [InlineData(DuckStyle.Mallard)]
    [InlineData(DuckStyle.Rubber)]
    public void A_fixed_setting_is_used_for_everyone(DuckStyle setting)
    {
        Assert.Equal(setting, StylePicker.Pick(setting, "Ann"));
        Assert.Equal(setting, StylePicker.Pick(setting, "Bob"));
        Assert.Equal(setting, StylePicker.Pick(setting, null));
    }

    [Fact]
    public void Random_gives_the_same_duck_for_the_same_name_every_time()
    {
        var first = StylePicker.Pick(DuckStyle.Random, "Visitor Carla Jones");
        for (var i = 0; i < 10; i++)
            Assert.Equal(first, StylePicker.Pick(DuckStyle.Random, "Visitor Carla Jones"));
    }

    [Fact]
    public void Random_uses_a_hash_that_does_not_change_between_runs()
    {
        // FNV-1a test vectors; string.GetHashCode would differ per process.
        Assert.Equal(2166136261u, StylePicker.Fnv1a(""));
        Assert.Equal(0xE40C292Cu, StylePicker.Fnv1a("a"));
        Assert.Equal(0xBF9CF968u, StylePicker.Fnv1a("foobar"));
    }

    [Fact]
    public void Random_spreads_names_over_all_three_ducks()
    {
        var counts = Enumerable.Range(0, 1000)
            .Select(i => StylePicker.Pick(DuckStyle.Random, $"Guest {i}"))
            .GroupBy(s => s)
            .ToDictionary(g => g.Key, g => g.Count());
        Assert.Equal(3, counts.Count);
        Assert.All(counts.Values, c => Assert.InRange(c, 250, 420));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    public void Random_without_a_name_gives_classic(string? name)
    {
        Assert.Equal(DuckStyle.Classic, StylePicker.Pick(DuckStyle.Random, name));
    }

    [Fact]
    public void Random_only_picks_styles_that_loaded()
    {
        var available = new[] { DuckStyle.Mallard, DuckStyle.Rubber };
        for (var i = 0; i < 200; i++)
            Assert.NotEqual(DuckStyle.Classic, StylePicker.Pick(DuckStyle.Random, $"Guest {i}", available));
    }

    [Fact]
    public void A_fixed_style_that_failed_to_load_falls_back_to_the_first_available()
    {
        Assert.Equal(DuckStyle.Rubber, StylePicker.Pick(DuckStyle.Classic, "Ann", new[] { DuckStyle.Rubber }));
    }

    [Fact]
    public void No_available_styles_is_an_error()
    {
        Assert.Throws<ArgumentException>(() => StylePicker.Pick(DuckStyle.Random, "Ann", Array.Empty<DuckStyle>()));
    }
}
