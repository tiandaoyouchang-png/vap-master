# VAP Master

[English](#english) | [简体中文](#简体中文)

---

<a name="english"></a>
## 🚀 Project Overview / 项目概览

`vap-master` is a professional, unified CLI tool designed to streamline the generation of Tencent VAP (Video Animation Player) MP4 files from PNG sequences. It serves as a powerful wrapper around the official VapTool Java API, offering advanced features such as automatic frame normalization and custom layout post-processing.

### ✨ Key Features / 核心特性

- **Unified Interface**: Simplifies the VAP generation process into a single command.
- **Multiple Layout Modes**: Supports both the `standard` VAP layout and a specialized `mask-left` layout.
- **Automatic Normalization**: Automatically detects frame dimensions and crops frames from `target_h + 10` height to `target_h` height (e.g., 1344px to 1334px) to meet specific platform requirements.
- **Dynamic Resolution**: Automatically adapts the output video resolution based on the input PNG frames (Width = FrameWidth * 2, Height = FrameHeight).
- **Advanced Post-Processing**: Handles complex region swapping and `vapc` atom manipulation for custom layouts.
- **Headless Execution**: Wraps the VapTool Java API for seamless integration into automated pipelines.

### 📂 Project Structure / 项目结构

- `vap_master.py`: Main CLI entry point. (主命令行入口脚本)
- `VapBatch.java`: Java wrapper for VapTool API. (VapTool API 的 Java 封装类)
- `VapBatch.class`: Compiled Java bytecode. (编译后的 Java 字节码文件)

### 🛠 Prerequisites / 前置条件

To use `vap-master`, ensure your environment meets the following requirements:

- **Java Runtime**: Java 17 or higher.
- **VapTool**: VapTool version 2.0.6 (requires `animtool.jar` and `mp4edit`).
- **FFmpeg Suite**: `ffmpeg` and `ffprobe` must be installed and available in your system's `PATH`.

### 📦 Installation / 安装

1. Clone or copy the `vap-master` directory to your local machine.
2. Ensure the `vap_master.py` script is executable:
   ```bash
   chmod +x vap_master.py
   ```
3. Verify that the default paths for Java and VapTool in `vap_master.py` match your environment, or provide them via CLI arguments.

### 📖 Usage / 使用方法

#### Standard Mode
Generates a VAP MP4 with the default layout: RGB on the left, Alpha on the right (scaled to 0.5x by default, configurable via `--standard-scale`).

```bash
python3 vap_master.py \
  --input /path/to/png_sequence \
  --output /path/to/output.mp4 \
  --fps 25 \
  --mode standard
```

#### Mask-Left Mode
Generates a VAP MP4 with a custom layout: Alpha/Mask on the left, RGB on the right. The output resolution is automatically calculated (Total Width = FrameWidth * 2, Height = FrameHeight).

```bash
python3 vap_master.py \
  --input /path/to/png_sequence \
  --output /path/to/output.mp4 \
  --fps 25 \
  --mode mask-left
```

### ⚙️ CLI Arguments / 命令行参数

| Argument | Description | Default |
| :--- | :--- | :--- |
| `--input` | **Required**. Path to the directory containing the PNG sequence. | N/A |
| `--output` | **Required**. Path where the final MP4 will be saved. | N/A |
| `--fps` | Frames per second for the output video. | `25` |
| `--mode` | Layout mode: `standard` or `mask-left`. | `standard` |
| `--standard-scale` | Alpha scaling factor for `standard` mode. | `0.5` |
| `--bitrate` | VapTool encoding bitrate in kbps. | `2000` |
| `--swap-bitrate` | Re-encoding bitrate for `mask-left` mode in kbps. | `3000` |
| `--java` | Path to the `java` binary. | *System Default* |
| `--vaptool-home` | Path to the VapTool home directory. | *System Default* |
| `--keep-work` | Keep the temporary working directory for debugging. | `False` |

### 🔍 Technical Details / 技术细节

#### Layout Specifications

- **Standard Mode**:
  - **Left**: RGB (Original size)
  - **Right**: Alpha (Scaled by `--standard-scale`, default 0.5x)
- **Mask-Left Mode**:
  - **Left**: Alpha/Mask (FrameWidth x FrameHeight)
  - **Right**: RGB (FrameWidth x FrameHeight)
  - **Total Resolution**: (FrameWidth * 2) x FrameHeight

#### Frame Normalization
The tool automatically detects dimensions from the first frame. If the raw height (`raw_h`) is exactly `target_h + 10` (e.g., 1344px vs 1334px), it will automatically crop the frame from the top (0,0) to `target_h` to ensure compatibility with specific VAP requirements.

#### Mask-Left Workflow
When running in `mask-left` mode, the tool performs the following steps:
1. **Initial Encoding**: Uses VapTool to generate a standard VAP MP4.
2. **Region Swapping**: Uses FFmpeg to re-encode the video, swapping the Alpha and RGB regions to the specified positions.
3. **Atom Manipulation**: Manually parses and updates the `vapc` atom within the MP4 container using `mp4edit` to ensure the player correctly interprets the new layout.

### ❓ Troubleshooting / 故障排除

- **Missing Dependencies**: Ensure `ffmpeg`, `ffprobe`, and `java` are correctly installed and accessible.
- **Invalid Frame Sizes**: Ensure all input PNGs have consistent dimensions. The tool supports dynamic resolution but requires uniform input frames.
- **VapTool Errors**: Check the VapTool home directory path and ensure `animtool.jar` is present.
- **Playback Issues**: If the video doesn't play correctly in `mask-left` mode, verify that the target player supports custom `vapc` configurations.

---

<a name="简体中文"></a>
## 🚀 Project Overview / 项目概览

`vap-master` 是一个专业且统一的命令行工具（CLI），旨在简化从 PNG 序列生成腾讯 VAP（Video Animation Player）MP4 文件的过程。它是对官方 VapTool Java API 的强大封装，提供了诸如自动帧规格化和自定义布局后处理等高级功能。

### ✨ Key Features / 核心特性

- **统一接口**：将 VAP 生成过程简化为单个命令。
- **多种布局模式**：支持“标准”（standard）VAP 布局和专门的“左侧蒙版”（mask-left）布局。
- **自动规格化**：自动检测帧尺寸，并将帧高度从 `target_h + 10` 裁剪至 `target_h`（例如从 1344px 裁剪至 1334px），以满足特定平台的规格要求。
- **动态分辨率适配**：根据输入 PNG 帧自动调整输出视频分辨率（宽度 = 帧宽 * 2，高度 = 帧高）。
- **高级后处理**：处理复杂的区域交换和 `vapc` atom 操作，以实现自定义布局。
- **无头执行**：封装了 VapTool Java API，可无缝集成到自动化流水线中。

### 📂 Project Structure / 项目结构

- `vap_master.py`: Main CLI entry point. (主命令行入口脚本)
- `VapBatch.java`: Java wrapper for VapTool API. (VapTool API 的 Java 封装类)
- `VapBatch.class`: Compiled Java bytecode. (编译后的 Java 字节码文件)

### 🛠 Prerequisites / 前置条件

在使用 `vap-master` 之前，请确保您的环境满足以下要求：

- **Java 运行时**：Java 17 或更高版本。
- **VapTool**：VapTool 2.0.6 版本（需要 `animtool.jar` 和 `mp4edit`）。
- **FFmpeg 套件**：必须安装 `ffmpeg` 和 `ffprobe` 并将其添加到系统的 `PATH` 中。

### 📦 Installation / 安装

1. 将 `vap-master` 目录克隆或复制到本地机器。
2. 确保 `vap_master.py` 脚本具有可执行权限：
   ```bash
   chmod +x vap_master.py
   ```
3. 验证 `vap_master.py` 中 Java 和 VapTool 的默认路径是否与您的环境匹配，或者通过命令行参数提供。

### 📖 Usage / 使用方法

#### 标准模式 (Standard Mode)
生成具有默认布局的 VAP MP4：左侧为 RGB，右侧为 Alpha（默认缩放至 0.5 倍，可通过 `--standard-scale` 配置）。

```bash
python3 vap_master.py \
  --input /path/to/png_sequence \
  --output /path/to/output.mp4 \
  --fps 25 \
  --mode standard
```

#### 左侧蒙版模式 (Mask-Left Mode)
生成具有自定义布局的 VAP MP4：左侧为 Alpha/蒙版，右侧为 RGB。输出分辨率将自动计算（总宽度 = 帧宽 * 2，高度 = 帧高）。

```bash
python3 vap_master.py \
  --input /path/to/png_sequence \
  --output /path/to/output.mp4 \
  --fps 25 \
  --mode mask-left
```

### ⚙️ CLI Arguments / 命令行参数

| 参数 | 描述 | 默认值 |
| :--- | :--- | :--- |
| `--input` | **必填**。包含 PNG 序列的目录路径。 | N/A |
| `--output` | **必填**。最终 MP4 的保存路径。 | N/A |
| `--fps` | 输出视频的帧率。 | `25` |
| `--mode` | 布局模式：`standard` 或 `mask-left`。 | `standard` |
| `--standard-scale` | `standard` 模式下的 Alpha 缩放系数。 | `0.5` |
| `--bitrate` | VapTool 编码比特率 (kbps)。 | `2000` |
| `--swap-bitrate` | `mask-left` 模式下的重编码比特率 (kbps)。 | `3000` |
| `--java` | `java` 二进制文件的路径。 | *系统默认* |
| `--vaptool-home` | VapTool 根目录路径。 | *系统默认* |
| `--keep-work` | 保留临时工作目录以便调试。 | `False` |

### 🔍 Technical Details / 技术细节

#### 布局规格

- **标准模式 (Standard Mode)**：
  - **左侧**：RGB（原始尺寸）
  - **右侧**：Alpha（按 `--standard-scale` 缩放，默认 0.5 倍）
- **左侧蒙版模式 (Mask-Left Mode)**：
  - **左侧**：Alpha/蒙版 (帧宽 x 帧高)
  - **右侧**：RGB (帧宽 x 帧高)
  - **总分辨率**：(帧宽 * 2) x 帧高

#### 帧规格化 (Frame Normalization)
该工具会自动从第一帧检测尺寸。如果原始高度 (`raw_h`) 正好是 `target_h + 10`（例如 1344px 与 1334px），它将自动从顶部 (0,0) 开始将帧裁剪至 `target_h`，以确保与特定 VAP 要求的兼容性。

#### 左侧蒙版工作流 (Mask-Left Workflow)
在 `mask-left` 模式下运行时，该工具执行以下步骤：
1. **初始编码**：使用 VapTool 生成标准的 VAP MP4。
2. **区域交换**：使用 FFmpeg 对视频进行重编码，将 Alpha 和 RGB 区域交换到指定位置。
3. **Atom 操作**：使用 `mp4edit` 手动解析并更新 MP4 容器内的 `vapc` atom，以确保播放器能正确解析新布局。

### ❓ Troubleshooting / 故障排除

- **缺少依赖**：确保已正确安装并可访问 `ffmpeg`、`ffprobe` 和 `java`。
- **无效的帧尺寸**：确保所有输入 PNG 的尺寸一致。该工具支持动态分辨率，但要求输入帧规格统一。
- **VapTool 错误**：检查 VapTool 根目录路径并确保 `animtool.jar` 存在。
- **播放问题**：如果视频在 `mask-left` 模式下无法正常播放，请验证目标播放器是否支持自定义 `vapc` 配置。


