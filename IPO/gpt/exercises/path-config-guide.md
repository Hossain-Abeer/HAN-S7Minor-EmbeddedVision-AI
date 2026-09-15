**Context handoff — IPO workflow**

Repo: `HAN-S7Minor-EmbeddedVision-AI` (GitHub, cloned on two Windows laptops with different usernames).

Structure: `IPO/[EX]/` — one folder per exercise, unzipped from Brightspace.

OpenCV: built from source at `C:\dev\opencv-build\opencv-install\x64\mingw\lib` (identical path on both laptops). `C:\dev\opencv-build\opencv-install\x64\mingw\bin` is on system PATH. Version 4.12.0.

Per-exercise `CMakeLists.txt`:
```cmake
set(OpenCV_DIR "C:/dev/opencv-build/opencv-install/x64/mingw/lib")
```
before `find_package(OpenCV REQUIRED)`.

Per-exercise Root `.vscode/settings.json`:
```json
"cmake.sourceDirectory": "${workspaceFolder}/IPO/[EX]",
"cmake.buildDirectory": "${sourceDir}/build"
```

Build/run: VS Code CMake panel → Delete Cache & Reconfigure → `F7` → run `IPO/[EX]/build/[EX].exe`.

Sync: VS Code Source Control → Commit → Sync/Push. Other laptop: `git pull`, rebuild.

`.gitignore`: `build/`, `*.exe`, `*.dll`, `CMakeCache.txt`, `CMakeFiles/`.

Status: `IPO/HelloVision` builds and runs. Next: remaining IPO exercises (HelloVision2, …).