# Duckify

A Waterpark Simulator mod that dresses every park visitor in the duck suit your mascot staff wear.

The suit is the game's own: the mascot's head, body suit and shoes, which the game keeps in its normal clothing tables. Duckify puts those on visitors in place of their clothes.

- Every visitor wears the suit, children and adults alike. Men get the male suit and women the female one; the game has no colour or other variants of it.
- Swimsuit changes and the clothes the game re-rolls during a visit end up as the suit too.
- The game's own events that change visitors' clothes still win. During the duck-head event, for example, visitors wear the duck helmet with the rest of the suit.
- Staff, the player and story characters keep their own clothes.

## Multiplayer

Duckify only changes what your own game draws. Visitors' real outfits are what the host saves and sends to other players, so players without the mod see the normal clothes, and your saves keep them too. If you remove the mod, visitors wear their own clothes again.

## Status

Early. Which suit piece fits which clothing slot, and the record of each visitor's own clothes, are covered by tests. In play, visitors wear the suit and turning `Enabled` off and on dresses them back and forth. Multiplayer has not been tried.

## Install

With [r2modman](https://thunderstore.io/package/ebkr/r2modman/): select Waterpark Simulator, install `BepInExPack_IL2CPP`, then install Duckify.

By hand: install BepInEx 6 (IL2CPP) for the game, then copy `Duckify.Plugin.dll` and `Duckify.Core.dll` into `BepInEx/plugins/Duckify/`.

## Settings

`BepInEx/config/com.github.kirby1997.duckify.cfg`, also editable in game with [ModSettings](https://thunderstore.io/c/waterpark-simulator/p/KirbyTeam/ModSettings/):

| Setting | Default | Meaning |
|---|---|---|
| `Enabled` | `true` | Dress visitors in the suit. Turning it off gives every visitor in the park their own clothes back at once |

## Building

Requirements: the .NET SDK 8 or newer, the game, and BepInExPack_IL2CPP installed through r2modman. Start the game once with BepInEx installed so it generates `BepInEx/interop`.

```
dotnet test
dotnet build -c Release
```

The build copies the plugin into the r2modman `Default` profile. To use another location, create `GamePaths.user.props` next to `GamePaths.props`:

```xml
<Project>
  <PropertyGroup>
    <ProfileDir>D:\path\to\profile</ProfileDir>
  </PropertyGroup>
</Project>
```

To build the Thunderstore package into `dist/`:

```
dotnet build src/Duckify.Plugin -c Release -t:PackThunderstore
```

## How it works

Every clothing change in the game ends in `CharacterCustomization.setApparel(selection, slot, material)`. A Harmony prefix swaps a visitor's pick for the suit piece in that slot's table (a `Mascot_` item), or for the empty entry where the suit has no piece (top and glasses). The mod keeps its own record of what the game asked each visitor to wear, which is what turning `Enabled` off and on dresses them in.

Inside `setApparel` the game's conflict solver reacts to what went on, for example by taking the top off under a full-body suit. Those nested calls are reactions to the suit, so they are not recorded. `setApparel` also writes the visitor's stored character data; after a swap, a postfix puts that data back as it was, with the visitor's own pick in the changed slot.

## Layout

- `src/Duckify.Core` has no game references: choosing the suit piece for a clothing table, and the record of each visitor's own clothes. This is where the tests point.
- `src/Duckify.Plugin` is the BepInEx plugin: the hooks on `setApparel`, redressing visitors and the `Enabled` setting.
- `tests/Duckify.Tests` are the xUnit tests for Core.

## License

MIT. Not affiliated with the developers of Waterpark Simulator.
