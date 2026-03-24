###[converter_GUI.exe](https://github.com/lian-rla/converter_GUI/releases/tag/converter_GUI)


# SEC Extension Converter

> A GUI-based video conversion tool that converts `.sec` video files from DVR systems into your desired format.  
> **Developed by LeeLab**

---

## User Guide (PDF)

> A detailed visual guide is available as a PDF — click the link below to view step-by-step instructions with screenshots.

### [View Full User Guide (PDF)]([converter 사용 가이드.pdf](https://github.com/user-attachments/files/26217869/converter.pdf))

---

## Introduction

This program was created to convert `.sec` extension video files — a proprietary format used by security DVR systems — into standard video formats.  
It uses FFmpeg internally and provides an intuitive GUI that anyone can use, even without a technical background.

---

## Key Features

<img width="1468" height="1125" alt="Image" src="https://github.com/user-attachments/assets/c7fc505e-5d58-4698-af07-ec8a814aa39e" />

| Feature | Description |
|------|------|
| **1. Batch Folder Conversion** | Select a parent folder and the tool automatically scans all subfolders for `.sec` files and converts them |
| **2. Single File Conversion** | Select and convert a single `.sec` file individually |
| **3. Output Format Selection** | Choose from `.mp4 (H.264)`, `.avi (MPEG-4)`, or `.mov (H.264)` — with options to set Framerate, CRF (quality), and Scale (resolution ratio) |
| **4. Real-time Progress** | Displays overall file progress and current file progress via progress bars |
| **5. Log Output** | Real-time log window showing which file is being converted and whether it succeeded or failed |

---

## Getting Started

### Method 1: Using the EXE Executable (Recommended)

The easiest method — no Python environment required.

**① Unzip the archive and open the `dist` folder**

**② Double-click `ExtensionConverter.exe` to launch**

**③ Confirm the program opens successfully**

> If a Windows security warning appears, click "More info" → "Run anyway".

---

### Method 2: Running the Python Script Directly

EXE 파일이 정상적으로 실행되지 않는 경우에만 이 방법을 사용합니다.

#### Step 1. Install FFmpeg

Download the FFmpeg Windows build from the link below and extract it.  
https://www.gyan.dev/ffmpeg/builds/

> Download `ffmpeg-release-essentials.zip` and extract it to your preferred path  
> e.g. `C:\ffmpeg-7.1.1-essentials_build`

#### Step 2. Set Environment Variables

Register FFmpeg in your PATH so it can be run from anywhere on the system.

**① Type "environment variables" in the Windows search bar and open "Edit the system environment variables"**

**② Click the [Environment Variables] button**

**③ Select `Path` under User Variables and click [Edit]**

**④ Click [New] and enter the path to the FFmpeg `bin` folder**

> Example: `C:\ffmpeg-7.1.1-essentials_build\bin`  
> ※ Repeat the same steps for System Variables as well.

#### Step 3. Set Up Python Environment

- Install [VS Code](https://code.visualstudio.com/) or another Python development tool first.
- Python 3.x must be installed on your system.

#### Step 4. Run the Script

```bash
python extension_converter.py
```

---

## How to Use

### 1. Batch Folder Conversion

Use this when `.sec` files are spread across multiple subfolders.

**① Click [Select Parent Folder] → Choose the parent folder containing `.sec` files**

**② Click [Convert All in Selected Folder]**

> The program will recursively scan all subfolders under the selected parent folder,  
> find `.sec` files, and save the converted output into a new folder named `foldername_mp4` (or your chosen extension).

**③ Check the output folder after conversion is complete**

**Example folder structure:**

```
📁 ParentFolder/
├── 📁 CAM01/
│   ├── video1.sec
│   └── video2.sec
└── 📁 CAM02/
    └── video3.sec
```

After conversion:

```
📁 ParentFolder/
├── 📁 CAM01/
│   └── ...
├── 📁 CAM01_mp4/          ← Auto-created
│   ├── video1.mp4
│   └── video2.mp4
├── 📁 CAM02/
│   └── ...
└── 📁 CAM02_mp4/          ← Auto-created
    └── video3.mp4
```

---

### 2. Single File Conversion

Use this when you only need to convert one `.sec` file.

**① Click [Select .sec File] → Choose the `.sec` file to convert**  
**② Click [Convert Selected File]**

The converted file will be saved in the **same folder** as the original `.sec` file.

---

### 3. FFmpeg Options

Adjust the conversion settings in the **FFmpeg Options** section before starting.

<img width="1830" height="447" alt="Image" src="https://github.com/user-attachments/assets/98530d7b-b333-4816-b7cf-ab83cb310c60" />

| Option | Description | Default | Recommended Range |
|------|------|--------|-----------|
| **Framerate** | Frames per second of the output video | `30` | Adjust based on DVR settings (e.g. 15, 30, 60) |
| **Quality (CRF)** | Lower = higher quality; higher = smaller file size | `23` | `0 ~ 51` (recommended `23` to preserve original quality) |
| **Resolution (Scale)** | Scale ratio relative to the original resolution | (empty = original) | e.g. `0.5` → 1920×1080 becomes 960×540 |
| **Output Extension** | Choose the output file format | `.mp4` | `.mp4 (H.264)` / `.avi (MPEG-4)` / `.mov (H.264)` |

> Framerate and resolution may vary depending on the DVR environment. Please check the source file info before converting.

---

### 4. Checking Progress

Once conversion starts, you can monitor the status in real time at the bottom of the screen.

- **Overall Progress Bar**: Shows how many files have been completed out of the total (e.g. `1/4 (25.0%)`)
- **Current File Progress Bar**: Shows the progress of the file currently being converted
- **Log Window**: Displays real-time logs including which file is being processed, success/failure status, and elapsed time

---

## Output File Structure

- **Batch Conversion**: A new folder named `originalfoldername_extension` is created next to the source folder
- **Single File Conversion**: The converted file is saved in the same directory as the original `.sec` file

---

## Notes

- Only **`.sec` extension** files are supported as conversion input.
- If the first conversion attempt fails, the tool will automatically retry using **fallback (forced conversion) mode**.
- CRF value must be an integer between `0` and `51`. Values outside this range will fall back to the default.
- Scale value must be a positive decimal number (e.g. `0.5`, `0.75`, `1.5`).
- If the EXE file runs correctly, it is recommended over running the `.py` script directly.
- When running the `.py` script, FFmpeg must be properly registered in the system PATH beforehand.
