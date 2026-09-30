namespace Duckify.Tests;

public class BoneMapTests
{
    [Fact]
    public void Maps_each_duck_bone_to_its_position_in_the_target()
    {
        var map = BoneMap.Build(new[] { "head", "pelvis", "hand_l" }, new[] { "root", "pelvis", "hand_l", "head" });

        Assert.True(map.IsComplete);
        Assert.Equal(new[] { 3, 1, 2 }, map.DuckToTarget);
        Assert.Empty(map.Missing);
    }

    [Fact]
    public void Names_the_bones_the_target_lacks()
    {
        var map = BoneMap.Build(new[] { "head", "tail_01", "pelvis", "wing_02" }, new[] { "pelvis", "head" });

        Assert.False(map.IsComplete);
        Assert.Equal(new[] { "tail_01", "wing_02" }, map.Missing);
        Assert.Equal(new[] { 1, -1, 0, -1 }, map.DuckToTarget);
    }

    [Fact]
    public void Uses_the_first_match_when_the_target_repeats_a_name()
    {
        var map = BoneMap.Build(new[] { "head" }, new[] { "head", "head" });
        Assert.Equal(new[] { 0 }, map.DuckToTarget);
    }

    [Fact]
    public void Names_are_case_sensitive_like_Unity()
    {
        var map = BoneMap.Build(new[] { "Head" }, new[] { "head" });
        Assert.Equal(new[] { "Head" }, map.Missing);
    }
}
