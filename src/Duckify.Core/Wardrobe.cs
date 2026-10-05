namespace Duckify.Core;

/// <summary>One slot of a character's outfit: which entry of the slot's apparel table, in which material.</summary>
public readonly record struct Pick(int Slot, int Selection, int Material);

/// <summary>
/// The clothes the game put on each character, slot by slot, before the suit replaced them. Turning
/// the suit off or on dresses visitors again from here. Characters are keyed by the address of their
/// customisation component, so the plugin drops the ones that left with <see cref="KeepOnly"/>.
/// </summary>
public sealed class Wardrobe
{
    private readonly Dictionary<long, SortedDictionary<int, Pick>> _outfits = new();

    /// <summary>How many characters have a recorded outfit.</summary>
    public int Count => _outfits.Count;

    public void Record(long character, int slot, int selection, int material)
    {
        if (!_outfits.TryGetValue(character, out var outfit)) _outfits[character] = outfit = new SortedDictionary<int, Pick>();
        outfit[slot] = new Pick(slot, selection, material);
    }

    public bool Has(long character, int slot) => _outfits.TryGetValue(character, out var outfit) && outfit.ContainsKey(slot);

    /// <summary>The recorded picks of one character, lowest slot first. Empty when nothing was recorded.</summary>
    public IReadOnlyList<Pick> Outfit(long character) =>
        _outfits.TryGetValue(character, out var outfit) ? outfit.Values.ToArray() : Array.Empty<Pick>();

    public void KeepOnly(IEnumerable<long> characters)
    {
        var live = new HashSet<long>(characters);
        foreach (var gone in _outfits.Keys.Where(k => !live.Contains(k)).ToList()) _outfits.Remove(gone);
    }
}
