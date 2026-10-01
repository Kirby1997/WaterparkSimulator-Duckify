namespace Duckify.Tests;

public class ArtFilesTests
{
    private static readonly string ArtDir = Path.Combine(AppContext.BaseDirectory, "art");

    public static IEnumerable<object[]> AllMeshes() =>
        from style in StylePicker.Concrete
        from sex in new[] { DuckSex.Male, DuckSex.Female }
        from part in new[] { DuckPart.Body, DuckPart.Wings }
        select new object[] { style, sex, part };

    private static DuckMeshData Load(DuckStyle style, DuckSex sex, DuckPart part)
    {
        var path = Path.Combine(ArtDir, DuckNames.FileName(style, sex, part));
        Assert.True(File.Exists(path), $"{path} is missing. Run art/build_ducks.py (see README).");
        using var stream = File.OpenRead(path);
        return DuckMeshReader.Read(stream);
    }

    [Theory]
    [MemberData(nameof(AllMeshes))]
    public void Every_shipped_duck_is_valid_and_within_budget(DuckStyle style, DuckSex sex, DuckPart part)
    {
        var mesh = Load(style, sex, part);

        Assert.All(mesh.Bones, b => Assert.Contains(b, Skeleton.BoneNames));
        Assert.InRange(mesh.TriangleCount, 200, part == DuckPart.Body ? 7000 : 2000);
        Assert.InRange(mesh.Submeshes.Length, 1, 8);
    }

    [Theory]
    [MemberData(nameof(AllMeshes))]
    public void Wings_follow_only_the_arms_and_bodies_use_the_head(DuckStyle style, DuckSex sex, DuckPart part)
    {
        var mesh = Load(style, sex, part);
        if (part == DuckPart.Wings)
        {
            Assert.DoesNotContain("head", mesh.Bones);
            Assert.DoesNotContain(mesh.Bones, b => b.StartsWith("thigh") || b.StartsWith("calf") || b.StartsWith("foot"));
            Assert.Contains("hand_l", mesh.Bones);
            Assert.Contains("hand_r", mesh.Bones);
        }
        else
        {
            Assert.Contains("head", mesh.Bones);
            Assert.Contains("foot_l", mesh.Bones);
        }
    }

    [Fact]
    public void Ducks_stand_on_the_floor_and_are_taller_than_a_metre()
    {
        var mesh = Load(DuckStyle.Classic, DuckSex.Male, DuckPart.Body);
        var ys = Enumerable.Range(0, mesh.VertexCount).Select(v => mesh.Positions[v * 3 + 1]).ToArray();
        Assert.InRange(ys.Min(), -0.05f, 0.05f);
        Assert.InRange(ys.Max(), 1.5f, 2.3f);
    }
}
