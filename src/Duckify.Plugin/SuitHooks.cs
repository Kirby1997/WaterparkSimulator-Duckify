using CayplayMissions.CustomizationNew;
using CC;
using Duckify.Core;
using HarmonyLib;
using UnityEngine;

namespace Duckify.Plugin;

/// <summary>
/// Dresses every visitor in the mascot's duck suit. Each outfit change in the game ends in
/// CharacterCustomization.setApparel(selection, slot, material): a visitor loading in, the clothes the
/// host sends, swimsuit changes and the game's own event overrides. The prefix records what the game
/// asked for, then swaps it for the suit piece in that slot's table.
///
/// Inside setApparel the game reacts to what was put on: its conflict solver takes the top off under a
/// full-body suit by calling setApparelByName again. Those nested calls are reactions to the suit, not
/// the visitor's clothes, so they are not recorded.
///
/// setApparel also writes the visitor's stored character data, which the host sends to other players
/// and saves. The postfix of the outermost swap puts that data back as it was, with the visitor's own
/// pick in the changed slot, so the suit only exists on this screen.
///
/// No hook may throw: an exception escaping into native code takes the game down.
/// </summary>
[HarmonyPatch]
internal static class SuitHooks
{
    private readonly struct Table
    {
        public readonly int? Piece;
        public readonly int? Empty;

        public Table(int? piece, int? empty)
        {
            Piece = piece;
            Empty = empty;
        }
    }

    // The tables are game assets and live as long as the game.
    private static readonly Dictionary<IntPtr, Table> Tables = new();
    private static readonly Wardrobe Wardrobe = new();
    private static int _purgeAt = 512;

    // Swapped setApparel calls on the stack. A call made while one runs is the game reacting to the suit.
    private static int _swapsUnderway;

    internal struct Swap
    {
        public bool Done;
        public string Original;
        public byte OriginalMaterial;
        public string Piece;
        // Stored outfit before the outermost swap; null on nested swaps.
        public string[] Names;
        public byte[] Materials;
    }

    [HarmonyPrefix]
    [HarmonyPatch(typeof(CharacterCustomization), nameof(CharacterCustomization.setApparel))]
    private static void BeforeSetApparel(CharacterCustomization __instance, ref int selection, int slot, ref int materialSelection, out Swap __state)
    {
        __state = default;
        try
        {
            // Visitors are the only characters with the game's visitor outfit override; staff, NPCs and players lack it.
            if (__instance.GetComponent<VisitorsOutfitOverride>() == null) return;

            var nested = _swapsUnderway > 0;
            if (!nested) RecordPick(__instance, slot, selection, materialSelection);
            if (!Plugin.Instance.Enabled.Value) return;

            var tables = __instance.ApparelTables;
            if (tables == null || slot < 0 || slot >= tables.Count) return;
            var table = tables[slot];
            var items = table?.Items;
            if (items == null || selection < 0 || selection >= items.Count) return;
            var piece = Describe(table).Piece;
            if (piece == null || piece == selection) return;

            var swap = new Swap
            {
                Done = true,
                Original = items[selection].Name,
                OriginalMaterial = (byte)materialSelection,
                Piece = items[piece.Value].Name,
            };
            if (!nested)
            {
                var data = __instance.StoredCharacterData;
                swap.Names = Copy(data?.ApparelNames);
                swap.Materials = Copy(data?.ApparelMaterials);
            }
            __state = swap;
            _swapsUnderway++;
            selection = piece.Value;
            materialSelection = 0;
        }
        catch (Exception e)
        {
            __state = default;
            Plugin.Instance.ReportOnce("suit swap", e);
        }
    }

    [HarmonyPostfix]
    [HarmonyPatch(typeof(CharacterCustomization), nameof(CharacterCustomization.setApparel))]
    private static void AfterSetApparel(CharacterCustomization __instance, int slot, Swap __state)
    {
        if (!__state.Done) return;
        _swapsUnderway = Math.Max(0, _swapsUnderway - 1);
        if (__state.Names == null) return;
        try
        {
            var data = __instance.StoredCharacterData;
            var names = data?.ApparelNames;
            if (names != null)
            {
                for (var i = 0; i < names.Count; i++)
                {
                    string want;
                    // An event override in this slot is the game's own doing; keep what it wrote.
                    if (i == slot) want = names[i] == __state.Piece ? __state.Original : names[i];
                    else want = i < __state.Names.Length ? __state.Names[i] : names[i];
                    if (names[i] != want) names[i] = want;
                }
            }
            var materials = data?.ApparelMaterials;
            if (materials != null)
            {
                for (var i = 0; i < materials.Count; i++)
                {
                    var want = i == slot ? __state.OriginalMaterial : i < __state.Materials?.Length ? __state.Materials[i] : materials[i];
                    if (materials[i] != want) materials[i] = want;
                }
            }
        }
        catch (Exception e)
        {
            Plugin.Instance.ReportOnce("restoring a visitor's own outfit", e);
        }
    }

    /// <summary>
    /// Dresses every visitor again in the clothes the game gave them, which the prefix turns into the
    /// suit while the mod is enabled. Run when Enabled changes so the change shows at once.
    /// </summary>
    internal static void RedressVisitors()
    {
        // Inactive too: the game switches off the models of visitors out of sight.
        var live = new List<long>();
        foreach (var visitor in UnityEngine.Object.FindObjectsByType<VisitorsOutfitOverride>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            try
            {
                var character = visitor.GetComponent<CharacterCustomization>();
                if (character == null) continue;
                var key = character.Pointer.ToInt64();
                live.Add(key);

                var outfit = Wardrobe.Outfit(key);
                // A slot the game never dressed was empty; empty it again so the suit piece comes off (or goes on).
                var tables = character.ApparelTables;
                for (var slot = 0; tables != null && slot < tables.Count; slot++)
                {
                    if (Wardrobe.Has(key, slot) || tables[slot] == null) continue;
                    var empty = Describe(tables[slot]).Empty;
                    if (empty != null) character.setApparel(empty.Value, slot, 0, true);
                }
                foreach (var pick in outfit) character.setApparel(pick.Selection, pick.Slot, pick.Material, true);
            }
            catch (Exception e)
            {
                Plugin.Instance.ReportOnce("redressing a visitor", e);
            }
        }
        Wardrobe.KeepOnly(live);
        Plugin.Instance.Log.LogInfo($"Redressed {live.Count} visitors.");
    }

    private static void RecordPick(CharacterCustomization character, int slot, int selection, int material)
    {
        Wardrobe.Record(character.Pointer.ToInt64(), slot, selection, material);
        if (Wardrobe.Count < _purgeAt) return;
        // Visitors leave all day; forget the ones that are gone.
        var live = UnityEngine.Object.FindObjectsByType<VisitorsOutfitOverride>(FindObjectsInactive.Include, FindObjectsSortMode.None)
            .Select(v => v.GetComponent<CharacterCustomization>())
            .Where(c => c != null)
            .Select(c => c.Pointer.ToInt64())
            .Append(character.Pointer.ToInt64());
        Wardrobe.KeepOnly(live);
        _purgeAt = Math.Max(512, Wardrobe.Count * 2);
    }

    private static Table Describe(scrObj_Apparel table)
    {
        if (Tables.TryGetValue(table.Pointer, out var known)) return known;
        var items = table.Items;
        var names = new string[items?.Count ?? 0];
        for (var i = 0; i < names.Length; i++) names[i] = items[i].Name;
        return Tables[table.Pointer] = new Table(MascotSuit.Pick(names), MascotSuit.EmptyIndex(names));
    }

    private static string[] Copy(Il2CppSystem.Collections.Generic.List<string> list)
    {
        if (list == null) return null;
        var copy = new string[list.Count];
        for (var i = 0; i < copy.Length; i++) copy[i] = list[i];
        return copy;
    }

    private static byte[] Copy(Il2CppSystem.Collections.Generic.List<byte> list)
    {
        if (list == null) return null;
        var copy = new byte[list.Count];
        for (var i = 0; i < copy.Length; i++) copy[i] = list[i];
        return copy;
    }
}
