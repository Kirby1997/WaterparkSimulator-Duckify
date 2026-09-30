using BepInEx;
using BepInEx.Configuration;
using BepInEx.Unity.IL2CPP;
using Duckify.Core;

namespace Duckify.Plugin;

[BepInPlugin(Id, Name, Version)]
public sealed class Plugin : BasePlugin
{
    public const string Id = "com.github.kirby1997.duckify";
    public const string Name = "Duckify";
    public const string Version = "0.1.0";

    private readonly HashSet<string> _reported = new();

    internal static Plugin Instance { get; private set; }

    internal ConfigEntry<bool> Enabled { get; private set; }
    internal ConfigEntry<DuckStyle> Style { get; private set; }
    internal ConfigEntry<bool> ShowClothes { get; private set; }

    public override void Load()
    {
        Instance = this;
        Enabled = Config.Bind("General", "Enabled", true,
            "Draw every character as a duck. Turn off to see the game's humans again.");
        Style = Config.Bind("General", "DuckStyle", DuckStyle.Random,
            "Which duck to draw. Random gives each character a duck picked from their name, so they keep it across reloads.");
        ShowClothes = Config.Bind("General", "ShowClothes", false,
            "Draw the game's clothes over the ducks. Hats, glasses and shoes fit; shirts and trousers are made for a " +
            "human body and clip into or through the duck.");

        Log.LogInfo($"{Name} {Version} loaded");
    }

    internal void ReportOnce(string what, Exception e)
    {
        if (_reported.Add(what)) Log.LogError($"{what} failed: {e}");
    }
}
