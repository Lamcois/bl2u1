Bambu Studio → Snapmaker U1 3MF Converter — keeps color painting, supports and settings

Got a library of painted, carefully-tuned models in Bambu Studio (A1/P1/X1) and want to print them on your Snapmaker U1? No need to redo everything from scratch 👇
Introducing Bambu2U1 Converter — my remix built on top of the original bl2u1 project by josuanbn (https://github.com/josuanbn/bl2u1). Huge thanks to the original author — full credit for the idea and foundation goes to them 🙏

What it does:
✅ Converts .3mf projects from Bambu Studio to Snapmaker U1 format, opens directly in Snapmaker Orca
✅ Keeps your color painting intact — no repainting needed
✅ Keeps supports: auto, manual, painted support areas, enforcer/blocker volumes
✅ Handles projects with more than 4 colors (6, 8+…) — all original filaments are preserved; you map them to the U1's 4 slots at print time (filament mapping), and you can change each filament's color/material right in the tool

What my remix adds over the original:
🔧 Process settings mapping from Bambu to U1: infill patterns (including newer ones like Archimedean Chords and 2D Lattice), walls, ironing, fuzzy skin, scarf seam, bridges, supports — enum mappings verified directly against the BambuStudio and Snapmaker OrcaSlicer source code
🔧 Hardware parameters (acceleration, bed temps, machine gcode…) stay at proper U1 defaults — nothing gets wrongly carried over from the A1
🔧 4-color limit removed — the full original filament list is preserved
🔧 Packaged as a single portable .exe — no Python install needed, runs on any Windows machine, double-click and it opens your browser at http://127.0.0.1:8080
How to use: open the app → drop your .3mf → tweak colors/materials if you want → Convert → download and open in Snapmaker Orca (File → Open Project, load settings) → slice and print.
⚠️ Note: filament settings (temps, flow) use standard Snapmaker profiles since the two hotends differ — fine-tune for your own filament. Always check the Preview after converting.


Free tool — found a bug? Drop a comment and I'll fix it. Happy printing! 🎉
