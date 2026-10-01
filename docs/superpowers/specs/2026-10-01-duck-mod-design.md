# Duckify: every character in Waterpark Simulator becomes a duck

Date: 2026-10-01

## Goal

Replace every character's human body with a humanoid duck: visitors, staff, the mascot, your own
character (third person and first-person arms) and other players. The game's own animations,
poses and ragdoll must drive the ducks unchanged.

## Scope

In scope:

- A BepInEx 6 IL2CPP plugin (`BasePlugin`, net6.0), laid out, built and packed like ParkStats.
- Three custom duck styles made in Blender by script: **Classic** (white, orange bill, head tuft),
  **Mallard** (brown body, dark chest, green head, white neck ring, yellow bill) and **Rubber**
  (glossy yellow bath duck). The user rejected every free downloaded model.
- A male and a female build of each style, plus first-person wing meshes for each.
- Config: duck style (random per guest by default), clothes on or off, mod on or off. All apply
  live.

Out of scope for version 1:

- Textures. Ducks use flat colours.
- Duck LODs. One mesh per style and sex at every distance.
- Sounds (quacks) and new animations.

## Constraints

- The mod only changes what the local screen draws. It makes no RPCs and changes no game state.
  Each client that has the mod sees ducks; clients without it see humans.
- No Unity Editor. Duck meshes are built at runtime from data embedded in the plugin DLL.
- No game assets in the repo. The Blender pipeline reads the guest skeleton from the local game
  install at build time.
- Hooks must never throw (an exception that reaches native code crashes the game). Every game
  read is null-guarded.

## What the game gives us

Found by reading `resources.assets` and `sharedassets1.assets` with UnityPy, and the decompiled
interop signatures:

- Every character's body and each clothing piece is a `SkinnedMeshRenderer` bound to one shared
  89-bone skeleton with Unreal-style names (`root`, `pelvis`, `spine_01`..`spine_05`, `neck_01`,
  `head`, `clavicle_l`, `upperarm_l`, `hand_l`, finger bones, `thigh_l`, `calf_l`, `foot_l`,
  `ball_l`, plus `*_twist_*` and `*_wt` helper bones). Male and female skeletons have the same
  names in a different order and different proportions. The male body is 1.81 m tall, in A-pose.
- Body meshes: `CC_Body_Male_LOD0..3`, `CC_Body_Female_LOD0..3` (about 10.3k vertices at LOD0).
  Avatars: `CC_MaleAvatar`, `CC_FemaleAvatar`.
- First-person arms: `First_Person_Male` and `First_Person_Female` (about 2.4k vertices) on the
  same 89 bones, weighted only from the clavicles to the fingers. Held by
  `CharacterCustomiserUtility.firstPersonRenderer`.
- `CC.CharacterCustomization` (on visitors, staff and players) exposes `MainMesh` (body),
  `CharacterRenderers`, `HairObjects`, `ApparelObjects`, `FirstPersonApparelObjects`,
  `RemapBonesByName(List<SkinnedMeshRenderer>)` and an `onCharacterLoaded` event.
  `CharacterCustomiserUtility` adds `OnOutfitSetupComplete`, `firstPersonRenderer` and
  `IsPlayer`.
- `AILODSystem` switches `MaleLODRenderers` / `FemaleLODRenderers` by distance.
- Ages are `Teen`, `Adult`, `Senior` (no children), made by bone scaling (`ModifyBone`).
- The game's own `Duck_Helmet` apparel and the mascot suit use the shader
  `Shader Graphs/Attraction` (properties include `_BaseMap`). The body uses
  `Shader Graphs/Shader_CC_Skin`.
- The game already has a `DuckVisitorsParkEvent` that swaps visitors' heads for a duck head.

## Design

### Art pipeline (`art/`)

1. `extract_reference.py` (UnityPy, run with uv) reads the game install and writes the male and
   female body meshes, first-person arm meshes and skeletons to `art/ref/*.json`: vertices,
   normals, UVs, triangles, 4 bone weights per vertex, bone names in mesh order, bind poses and
   the transform hierarchy. `art/ref/` is git-ignored.
2. `duckgen.py` runs in headless Blender 5.2
   (`blender.exe --background --python`). For each sex it rebuilds the armature from the bind
   poses, then builds each style from primitives placed on bone positions. The primitives are fused
   with a voxel remesh, smoothed and decimated to about 6k triangles per duck.
3. Weights: copied from the matching human body with a Data Transfer modifier (nearest face,
   interpolated). Then head, bill, eyes and tuft are set to 100% `head`, each vertex keeps at most
   4 influences, and weights are normalised.
4. First-person wings: the arm section of the same duck (vertices whose weight is mostly on
   clavicle, arm, twist, hand or finger bones), cut out and closed at the shoulder. This matches
   what `First_Person_*` covers.
5. Export: one `.duckmesh` file per style × sex × {body, wings} (12 files) to `art/out/`, and a
   preview render of each duck. `.duckmesh` is a small little-endian binary:
   - header: magic `DUCK`, format version, vertex count, bone count, submesh count
   - bone name table (UTF-8), in the order the weights index
   - per submesh: an sRGB colour (RGBA8), a smoothness value, triangle indices
   - per vertex: position, normal (Unity space, metres), 4 bone indices, 4 weights

   No bind poses are stored. Each duck is modelled in the bind space of the matching game mesh
   (body or first-person arms, same sex), so at runtime the plugin reuses that renderer's own
   `sharedMesh.bindposes`, reordered by bone name.
   The coordinate conversion from Blender is the inverse of the one used on import
   (Unity `(x, y, z)` = Blender `(-x, z, -y)`), with triangle winding flipped back.
6. The build embeds `art/out/*.duckmesh` into the plugin DLL as resources. `art/out/` is
   committed: it holds only duck geometry made in this repo, no game data. Contributors without
   the game can build the plugin; only regenerating the ducks needs the game install.

### Core (`src/Duckify.Core`, net6.0, tested)

- `DuckStyle` enum: `Random`, `Classic`, `Mallard`, `Rubber`.
- `StylePicker.Pick(DuckStyle setting, string characterName)` → a concrete style. With `Random`
  it uses a stable hash of the name (FNV-1a, not `string.GetHashCode`, which changes between
  runs), so a guest keeps the same duck across reloads and on every client. An empty or null name
  gives `Classic`.
- `DuckMeshData` + `DuckMeshReader.Read(Stream)`: parses and checks a `.duckmesh` file. It rejects
  bad magic, an unknown version, out-of-range bone indices, weights that do not sum to 1 (±0.01)
  and triangle indices past the vertex count, with an error that names the problem.
- `BoneMap.Build(IReadOnlyList<string> duckBones, IReadOnlyList<string> targetBones)` → index map
  from duck bone order to the target renderer's bone order. It reports missing bones by name.

### Plugin (`src/Duckify.Plugin`, net6.0, nullable off)

- `Plugin` binds config and loads the 12 meshes from embedded resources once through Core.
- `DuckMeshFactory`: turns `DuckMeshData` + a target `SkinnedMeshRenderer` into a Unity `Mesh`
  whose bone indices follow the target's `bones` order (through `BoneMap`), with bind poses
  copied from the target's `sharedMesh.bindposes`. It picks the male or female duck from the
  target mesh name (`DuckNames.SexFromMeshName` in Core: names containing `Female` are female). It
  caches one `Mesh` per style × part × target mesh. Materials: one per colour, a new
  `Material` on the game's `Shader Graphs/Attraction` shader. That shader has no plain tint
  colour (checked offline: its properties are `_BaseMap`, `_ColorMasks`, `_Color1`..`_Color4`,
  `_OSM`, `_Smoothness`, `_Metallic` and others), so each colour is a 4×4 solid `Texture2D` set as
  `_BaseMap`, with `_ColorMasks` set to a black texture and `_Color1`..`_Color4` white.
  `Universal Render Pipeline/Lit` is not in the build, so there is no fallback shader: if
  `Attraction` cannot be found, characters stay human and the mod retries later.
- `Duckifier` (one per character, added as a component or tracked in a dictionary keyed by
  instance ID):
  - Adds a child GameObject `Duck` with a `SkinnedMeshRenderer` that shares `MainMesh.bones` and
    `rootBone`, copies its layer, shadow mode and `updateWhenOffscreen`, and uses the duck mesh
    for the character's sex.
  - Hides the human with `renderer.forceRenderingOff = true`, not `enabled = false`, so
    `AILODSystem` cannot switch it back on: `MainMesh`, the body LOD renderers and all hair.
    Apparel (third- and first-person) is hidden only when `ShowClothes` is off.
  - First person: when the character has a `firstPersonRenderer`, adds a `DuckWings` child that
    shares its bones and copies its layer (so the first-person camera draws it), and hides the
    human arms.
  - `Revert()` removes the duck objects and sets `forceRenderingOff = false` on everything it hid.
- Finding characters: a postfix on `CharacterCustomization.Start` (parameterless) registers each
  character as it spawns, and every 2 seconds `Object.FindObjectsByType<CharacterCustomization>`
  catches any the hook missed. A per-frame runner (`DuckRunner`, an injected `MonoBehaviour`)
  re-checks up to 20 characters per frame in turn, so outfit changes, sex changes and
  first-person renderers that appear later are picked up without knowing which game method
  finished the outfit. Every frame it also copies the human renderers' `enabled`, layer and
  shadow mode onto the duck, so LOD switches and first/third-person switches stay in step.
  Every hook and runner body is wrapped in try/catch and logs once per error type.
- Live config: every refresh reads the current config values, so a change reaches every tracked
  character within a few frames. No `SettingChanged` handler is needed.

### Config (`BepInEx/config/<guid>.cfg`, editable in game with ModSettings)

| Section | Key | Type | Default | Meaning |
|---|---|---|---|---|
| General | `Enabled` | bool | `true` | Off turns every duck back into a human. |
| General | `DuckStyle` | `Random` / `Classic` / `Mallard` / `Rubber` | `Random` | Random gives each character a duck picked from their name. |
| General | `ShowClothes` | bool | `false` | On draws the game's clothes over the duck. Hats, glasses and shoes fit; shirts and trousers are shaped for a human body and clip into or through the duck. |

### Repo layout

Same as ParkStats: `DuckMod/` with `Duckify.sln`, `GamePaths.props`, `src/Duckify.Core`,
`src/Duckify.Plugin`, `tests/Duckify.Tests`, `art/`, `thunderstore/`, `CHANGELOG.md`, `README.md`.
The version is kept in the same three places, and `PackThunderstore` checks they match. The README
credits nothing third-party: all duck art is made in this repo.

## Error handling

- A `.duckmesh` that fails to parse: log the reason, and that style is dropped from `Random`. If
  every style fails, the mod logs one error and does nothing.
- A target renderer missing a bone the duck needs: log the bone names once per skeleton and leave
  that character human.
- `Shader Graphs/Attraction` not found: leave characters human and try again on the next discovery pass.
- A character destroyed while tracked: drop it on the next apply pass (null check on the Unity
  object).

## Testing

- Core, xUnit (test-first): `StylePicker` (fixed setting, stable random across calls, spread over
  all three styles across 1,000 names, null name), `DuckMeshReader` (round-trip of a writer-built
  sample, each rejection case), `BoneMap` (reorder, missing bones).
- Art: `duckgen.py` asserts per duck: triangle budget (≤ 7k body, ≤ 2k wings), every vertex
  weighted, at most 4 influences, all bone names present in the skeleton. It also renders a posed
  check (walk frame and sit pose applied to the armature) for a visual review.
- In game, manual: visitors, staff, mascot, own character in third and first person, a second
  player, `ShowClothes` on/off live, `DuckStyle` switch live, `Enabled` off restores humans, the
  duck-head park event, a slide, the pool, a ragdoll (pick up and drop a guest).

## Risks to check first

1. Whether a new `Attraction` material with a solid `_BaseMap` looks right: `_OSM` and
   `_BaseNormal` defaults are unknown.
2. Whether the discovery sweep and `Start` hook catch visitors, staff, the local player and remote
   players, and how long a new guest shows as a human before it becomes a duck.
3. Whether `forceRenderingOff` survives `AILODSystem` and the customisation code.
4. Whether the first-person camera culls by layer, so `DuckWings` must match the arms' layer.
5. Whether `SetBlendShapeWeight` calls from the game hit the duck. They should not, because the
   duck is a separate renderer and the body renderer keeps its own mesh.
