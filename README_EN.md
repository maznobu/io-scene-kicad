# io-scene-kicad

## VRML2 export add-in for KiCad

This is an exporter from Blender to VRML2 files (.wrl) that can be used for KiCad. <br>
Export the mesh object to her WRL file for KiCad. <br>
The script interface language is Japanese.<br>
Operation has been confirmed with Blender 3.6 and 4.0.x.

### About release packages

Packages (.zip files) that can be installed in Blender can be found at [Releases](https://github.com/maznobu/io-scene-kicad/releases). <br>
Only .zip files in assets can be used. Source code (.zip | .tar.gz) cannot be used (I don't really understand how it works...).

### Installation

1. Open [Add-ons] from [Preferences] in Bleander.
2. Click [Install] in the upper right corner and select the distributed io_scene_kicad.zip.
3. [WRL(KiCad) Export] will be expanded in the add-on list of [Preferences], so
   Check it to enable the add-on.

### Basic operations

11. Create a full-size model in Blender. For 3mm parts, use 3mm.
12. If there is one part per file, create it centered around the world origin. It will be easier if you match it with the origin of the footprint.
13. If you want to create multiple parts in one file, place the top-level objects at different coordinates. If it consists of multiple meshes, add them as child objects.
14. Click the [Export] button from the [WRL (KiCad) Export] panel described above.
15. If there is one part per file, check the [Center on world coordinates] option. <br>
    If you want to create multiple parts in one file, uncheck [Center on world coordinates].
16. Click the [WRL (KiCad) Export] button to output the .wrl file.
17. Next is the operation on the KiCad side. Open KiCad's footprint editor and open any desired footprint in edit mode.
18. Open the property editing screen by editing footprint properties. There you will find a tab called 3D Model.
19. Click the [3D Model] tab and add a path using the [+] mark button. For detailed usage, please refer to KiCad help.
20. Select the .wrl file generated by this add-in. The 3D model you created will probably be displayed in the 3D view. If the position is off, please adjust it.
21. Press OK to close the editing screen and save the footprint. That's it!
</details>

### Detailed usage etc.

1. After installing this add-in, the [KiCad] tab will be displayed in the UI tools (tool list on the right side).
2. Click on the [KiCad] tab, the [WRL (KiCad) Export] panel will appear, and there will be a [Help] button. <br>
   For detailed usage information, please refer to this help.

<br>
<br>
<br>
<br>

## Development environment (as of March 1, 2024)

- Blender 4.0.2 (Intel 64bit)
- Visual Studio Code 1.86.2 (as of 3/1/2024)
  - Blender Development [Experimental Fork]
  - Japanese Language Pack for Visual Studio Code
- Workstation (Dell Precision T7600 or T7920)