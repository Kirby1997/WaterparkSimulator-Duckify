namespace Duckify.Core;

/// <summary>
/// Where each bone a duck mesh uses sits in a game renderer's bone list. Male and female game
/// skeletons share bone names but not their order, so ducks are matched by name.
/// </summary>
public sealed class BoneMap
{
    private BoneMap(int[] duckToTarget, IReadOnlyList<string> missing)
    {
        DuckToTarget = duckToTarget;
        Missing = missing;
    }

    /// <summary>For each duck bone, its index in the target's bones, or -1 when the target lacks it.</summary>
    public int[] DuckToTarget { get; }

    public IReadOnlyList<string> Missing { get; }

    public bool IsComplete => Missing.Count == 0;

    public static BoneMap Build(IReadOnlyList<string> duckBones, IReadOnlyList<string> targetBones)
    {
        var index = new Dictionary<string, int>(StringComparer.Ordinal);
        for (var i = 0; i < targetBones.Count; i++) index.TryAdd(targetBones[i], i);

        var map = new int[duckBones.Count];
        var missing = new List<string>();
        for (var i = 0; i < duckBones.Count; i++)
        {
            if (index.TryGetValue(duckBones[i], out var target))
            {
                map[i] = target;
            }
            else
            {
                map[i] = -1;
                missing.Add(duckBones[i]);
            }
        }
        return new BoneMap(map, missing);
    }
}
