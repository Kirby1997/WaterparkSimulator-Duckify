using BepInEx;
using BepInEx.Configuration;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;

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

    public override void Load()
    {
        Instance = this;
        Enabled = Config.Bind("General", "Enabled", true,
            "Dress every visitor in the park mascot's duck suit. Turn off to give them their own clothes back; " +
            "the change shows at once.");
        Enabled.SettingChanged += OnEnabledChanged;

        new Harmony(Id).PatchAll(typeof(SuitHooks));
        Log.LogInfo($"{Name} {Version} loaded");
    }

    private void OnEnabledChanged(object sender, EventArgs args)
    {
        try
        {
            SuitHooks.RedressVisitors();
        }
        catch (Exception e)
        {
            ReportOnce("redressing visitors", e);
        }
    }

    internal void ReportOnce(string what, Exception e)
    {
        if (_reported.Add(what)) Log.LogError($"{what} failed: {e}");
    }
}
