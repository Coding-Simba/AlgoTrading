I'm trying to load a new NinjaTrader 8 strategy (Tom3.cs) and it never appears in NT8's Strategy dialog. The actual problem now is that NT8 won't recompile the user assembly at all — it's running on the pristine baseline DLL that ships with the installer. Need a definitive way to force a recompile, or to surface why NT8 is silently skipping compile.

## System
- NinjaTrader 8.1.6.3 on Parallels-on-macOS (Windows 11 ARM64). User data folder is on the Mac side: `\\Mac\Home\Documents\NinjaTrader 8\`. NT8 was Repair-Installed once last night.

## What I've already done
1. Removed our broken AlgoTrading C# port (Strategy + 80 AddOn .cs files) — files moved to backup, csproj entries removed. Original cause of 64 CS0579 duplicate-attribute errors from `obj\Release\{locale}\NinjaTrader.Custom.resources.cs` (8 locales × 8 attributes — MSBuild auto-includes satellite-resource attribute files in main compile).
2. Patched csproj after reset with defensive items:
   ```xml
   <ItemGroup>
     <None Remove="obj\**" />
     <Page Remove="obj\**" />
     <Compile Remove="obj\**" />
     <EmbeddedResource Remove="obj\**" />
   </ItemGroup>
   <Target Name="RemoveGeneratedResourceAttributeSources" BeforeTargets="CoreCompile">
     <ItemGroup>
       <Compile Remove="obj\**\*.resources.cs" />
       <Compile Remove="$(BaseIntermediateOutputPath)**\*.resources.cs" />
       <Compile Remove="$(IntermediateOutputPath)**\*.resources.cs" />
     </ItemGroup>
   </Target>
   ```
3. Killed all NinjaTrader.exe processes, wiped `bin\Custom\obj\` and `bin\Custom\bin\` entirely.
4. Copied `Tom3.cs` into `bin\Custom\Strategies\` and added explicit `<Compile Include="Strategies\Tom3.cs" />` to csproj (csproj has `<EnableDefaultCompileItems>false</EnableDefaultCompileItems>`).
5. User launched NT8.

## Current state
- NT8 is running, connected to data feed, no "Uncompilable NinjaScript" dialog.
- `bin\Custom\NinjaTrader.Custom.dll` exists with timestamp `Jan 15 04:10` (NT8 build date) — 1,221,632 bytes. **This is the pristine baseline DLL from the installer, not a freshly-compiled one.**
- `bin\Custom\obj\` and `bin\Custom\bin\` **do not exist** — NT8 has not run MSBuild this session.
- `Tom3.cs` is on disk in `bin\Custom\Strategies\`.
- `Tom3` does **NOT** appear in the Strategy dialog (only the 4 `@Sample*` stubs that are in the baseline DLL).
- This session's full trace (`trace.20260511.00001.txt`, tail covered) has zero compile-related entries. Just normal startup, Tradovate adapter chatter, Sim data subscription errors (unrelated).

## Likely root cause (my best guess)
NT8 only triggers MSBuild when it detects a change "through its own editor" — e.g. saving a .cs via NinjaScript Editor or hitting F5. Externally adding a .cs file via Explorer/Finder doesn't bump a sentinel NT8 watches. Since the baseline DLL exists, NT8 considers itself "compiled" and never invokes MSBuild. Hence no compile errors logged, but Tom3 never gets in.

I see a file at `C:\Program Files\NinjaTrader 8\bin\Custom\Backup\NinjaTrader.Custom.dll` — that's the installer's baseline backup. The current `bin\Custom\NinjaTrader.Custom.dll` matches its timestamp. So NT8 is using exactly that file.

## Questions
1. **What is NT8's recompile-trigger mechanism?** Specifically: is there a sentinel file (`obj\Release\NinjaTra.EBC8F642.Up2Date` — I saw one in obj earlier — or a hash file) that NT8 checks at launch to decide whether to re-invoke MSBuild?
2. **How do I force NT8 to recompile** without manually clicking F5 in the editor? (User would prefer a launch-time fix so the strategy "just appears" — they're frustrated with the click-by-click workflow.)
3. **Is deleting `bin\Custom\NinjaTrader.Custom.dll` enough**, or does NT8 immediately copy the baseline back from `C:\Program Files\NinjaTrader 8\bin\Custom\Backup\` on startup (re-creating the same baseline)?
4. **Will pressing F5 in the editor right now actually do anything?** Or will NT8 see "DLL exists, looks fine" and refuse to recompile until something is dirty?
5. **Will my BeforeTargets="CoreCompile" target survive** when NT8's editor invokes compile? Or does NT8's editor use its own Roslyn pipeline that bypasses csproj targets entirely?

Best-of-three minimal-disruption fix paths I can think of:
- A) Edit Tom3.cs through NT8's NinjaScript Editor (any whitespace edit + Ctrl+S) — forces NT8 to mark assembly dirty.
- B) Delete `bin\Custom\NinjaTrader.Custom.dll` AND its `.pdb`/`.xml` AND any `Up2Date` sentinels, then start NT8 — hoping it sees "no DLL" and rebuilds.
- C) Touch the timestamp on a tracked `.cs` (e.g. `Strategies\@Strategy.cs`) so NT8 thinks the source is newer than the DLL.

Which is most likely to actually work? If none, what's the right move? Keep it tight, no preamble. Push back if my diagnosis is wrong.

## File paths for reference
- csproj: `\\Mac\Home\Documents\NinjaTrader 8\bin\Custom\NinjaTrader.Custom.csproj`
- baseline DLL: `C:\Program Files\NinjaTrader 8\bin\Custom\Backup\NinjaTrader.Custom.dll`
- deployed DLL (same content): `\\Mac\Home\Documents\NinjaTrader 8\bin\Custom\NinjaTrader.Custom.dll`
- Tom3 source: `\\Mac\Home\Documents\NinjaTrader 8\bin\Custom\Strategies\Tom3.cs`
- Latest trace: `\\Mac\Home\Documents\NinjaTrader 8\trace\trace.20260511.00001.txt`
