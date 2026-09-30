namespace Duckify.Tests;

public class DuckNamesTests
{
    [Theory]
    [InlineData(DuckStyle.Classic, DuckSex.Male, DuckPart.Body, "classic_male_body.duckmesh")]
    [InlineData(DuckStyle.Mallard, DuckSex.Female, DuckPart.Wings, "mallard_female_wings.duckmesh")]
    [InlineData(DuckStyle.Rubber, DuckSex.Female, DuckPart.Body, "rubber_female_body.duckmesh")]
    public void File_names_are_lower_case_style_sex_part(DuckStyle style, DuckSex sex, DuckPart part, string expected)
    {
        Assert.Equal(expected, DuckNames.FileName(style, sex, part));
    }

    [Fact]
    public void Random_has_no_file()
    {
        Assert.Throws<ArgumentException>(() => DuckNames.FileName(DuckStyle.Random, DuckSex.Male, DuckPart.Body));
    }

    [Theory]
    [InlineData("CC_Body_Female_LOD0", DuckSex.Female)]
    [InlineData("First_Person_Female", DuckSex.Female)]
    [InlineData("CC_Body_Male_LOD0", DuckSex.Male)]
    [InlineData("First_Person_Male", DuckSex.Male)]
    [InlineData("SomethingElse", DuckSex.Male)]
    [InlineData(null, DuckSex.Male)]
    public void Sex_comes_from_the_game_mesh_name(string? meshName, DuckSex expected)
    {
        Assert.Equal(expected, DuckNames.SexFromMeshName(meshName));
    }
}
