namespace Duckify.Tests;

public class WardrobeTests
{
    [Fact]
    public void Keeps_the_latest_pick_per_slot()
    {
        var wardrobe = new Wardrobe();
        wardrobe.Record(1, slot: 0, selection: 5, material: 2);
        wardrobe.Record(1, slot: 0, selection: 7, material: 1);
        wardrobe.Record(1, slot: 4, selection: 0, material: 0);

        Assert.Equal(new[] { new Pick(0, 7, 1), new Pick(4, 0, 0) }, wardrobe.Outfit(1));
    }

    [Fact]
    public void Characters_are_kept_apart()
    {
        var wardrobe = new Wardrobe();
        wardrobe.Record(1, 0, 5, 0);
        wardrobe.Record(2, 1, 3, 0);

        Assert.Equal(new[] { new Pick(0, 5, 0) }, wardrobe.Outfit(1));
        Assert.Equal(new[] { new Pick(1, 3, 0) }, wardrobe.Outfit(2));
        Assert.Empty(wardrobe.Outfit(3));
    }

    [Fact]
    public void Outfit_is_in_slot_order()
    {
        var wardrobe = new Wardrobe();
        wardrobe.Record(1, 4, 1, 0);
        wardrobe.Record(1, 0, 2, 0);
        wardrobe.Record(1, 2, 3, 0);

        Assert.Equal(new[] { 0, 2, 4 }, wardrobe.Outfit(1).Select(p => p.Slot));
    }

    [Fact]
    public void Has_tells_which_slots_were_recorded()
    {
        var wardrobe = new Wardrobe();
        wardrobe.Record(1, 2, 3, 0);

        Assert.True(wardrobe.Has(1, 2));
        Assert.False(wardrobe.Has(1, 0));
        Assert.False(wardrobe.Has(9, 2));
    }

    [Fact]
    public void Forgets_characters_that_are_gone()
    {
        var wardrobe = new Wardrobe();
        wardrobe.Record(1, 0, 5, 0);
        wardrobe.Record(2, 0, 6, 0);
        wardrobe.Record(3, 0, 7, 0);

        wardrobe.KeepOnly(new long[] { 2 });

        Assert.Empty(wardrobe.Outfit(1));
        Assert.Single(wardrobe.Outfit(2));
        Assert.Empty(wardrobe.Outfit(3));
        Assert.Equal(1, wardrobe.Count);
    }
}
