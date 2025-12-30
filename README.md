# Nopressure

**Nopressure** 是一款基于 PyQt5 开发的轻量级、专业级“摸鱼”绘图工具。它支持直接加载 Photoshop (`.abr`) 笔刷材质，并拥有极高的 UI 灵活性，旨在为用户提供一个高性能、低侵入感的随手涂鸦空间。

## ✨ 功能特性

* **专业笔刷支持**：内置强大的 ABR 解析器，支持 Photoshop 采样位图笔刷，并能自动处理 Alpha 遮罩与边缘反相逻辑。
* **极致响应式 UI**：彻底取消了最小宽度限制，窗口可缩放至极小尺寸，完美适配各种桌面角落。
* **双栏创作模式**：参考图与绘画区保持 1:1 比例，支持一键折叠参考图并自动同步调整窗口宽度。
* **高性能渲染引擎**：采用 NumPy 加速 RLE 解码，并在绘图循环外进行预上色处理，确保大尺寸笔刷依旧丝滑连贯。
* **完善的撤销系统**：支持多步撤销（Undo），准确记录每一个灵感瞬间。

## 🚀 快速开始

### 1. 环境要求
确保你的 Python 环境中已安装以下必要的依赖库：
bash
pip install PyQt5 numpy



### 2. 笔刷配置

1. 在程序脚本同级目录下创建一个名为 `brushes` 的文件夹。
2. 将你喜欢的 `.abr` 格式笔刷文件放入该文件夹中。
3. 程序启动时会自动扫描该目录，笔刷名称将以文件名形式显示在下拉菜单中。

### 3. 运行程序

bash
python Nopressure.py



## ⌨️ 快捷键说明

| 快捷键 | 功能描述 |
| --- | --- |
| **Q** | 开关顶部工具栏 |
| **W** | 开关参考图（自动缩放窗口宽度） |
| **C** | 清空当前画布 |
| **Ctrl + Z** | 撤销上一步操作 |
| **Ctrl + Y** | 重做上一步操作 |
| **Ctrl + S** | 保存画作为 PNG 图片 |

## 🛠️ 技术实现细节

* **材质提取**：通过深度解析 Photoshop 二进制格式中的 `8BIM` 签名与 `samp` 数据块，提取高精度位图材质。
* **色彩混合**：使用 `CompositionMode_SourceOver` 实现笔触的自然叠加，利用 `CompositionMode_DestinationIn` 实现动态上色。
* **性能优化**：针对 ABR 解析过程中的 NumPy 标量运算进行了溢出保护处理，提升了复杂画刷的载入速度。

## ⚖️ 开源署名与协议

本项目的 ABR 笔刷解析核心逻辑参考并修改自以下开源项目：

* **参考项目**：[Brush-Converter](https://github.com/tohsakrat/Brush-Converter)
* **开源协议**：[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.zh) (署名-非商业性使用)

**特别声明：** 根据 CC BY-NC 4.0 协议要求，本项目严禁用于任何形式的商业用途。

===============================================================================================================================================================

# Nopressure

**Nopressure** is a lightweight, professional-grade "slacking" drawing tool developed based on PyQt5. It supports direct loading of Photoshop (`.abr`) brush materials and features highly flexible UI, aiming to provide users with a high-performance, low-intrusive space for casual doodling.

## ✨ Feature Highlights
* **Professional Brush Support**: Built-in powerful ABR parser that supports Photoshop sampled bitmap brushes, with automatic handling of alpha masks and edge inversion logic.
* **Ultimate Responsive UI**: Completely removes minimum width restrictions, allowing the window to be scaled to an extremely small size for perfect adaptation to any corner of the desktop.
* **Two-Panel Creation Mode**: Maintains a 1:1 ratio between reference images and the drawing area, with one-click reference image folding and automatic synchronous adjustment of window width.
* **High-Performance Rendering Engine**: Adopts NumPy-accelerated RLE decoding and pre-coloring processing outside the drawing loop to ensure smooth performance even with large-size brushes.
* **Comprehensive Undo System**: Supports multi-step undo to accurately record every moment of inspiration.

## 🚀 Quick Start
### 1. Environment Requirements
Ensure the following required dependency libraries are installed in your Python environment:
bash
pip install PyQt5 numpy


### 2. Brush Configuration
1. Create a folder named `brushes` in the same directory as the program script.
2. Place your favorite `.abr` format brush files into this folder.
3. The program will automatically scan this directory on startup, and brush names will be displayed in the drop-down menu by their file names.

### 3. Run the Program
bash
python Nopressure.py


## ⌨️ Shortcut Key Instructions
| Shortcut Key | Function Description |
| --- | --- |
| **Q** | Toggle the top toolbar |
| **W** | Toggle reference images (automatically scales window width) |
| **C** | Clear the current canvas |
| **Ctrl + Z** | Undo the previous operation |
| **Ctrl + Y** | Redo the previous operation |
| **Ctrl + S** | Save the artwork as a PNG image |

## 🛠️ Technical Implementation Details
* **Material Extraction**: Extracts high-precision bitmap materials by deeply parsing the `8BIM` signature and `samp` data blocks in the Photoshop binary format.
* **Color Blending**: Uses `CompositionMode_SourceOver` to achieve natural overlay of brush strokes, and `CompositionMode_DestinationIn` for dynamic coloring.
* **Performance Optimization**: Implements overflow protection for NumPy scalar operations during ABR parsing to improve loading speed of complex brushes.

## ⚖️ Open Source Attribution and License
The core logic of ABR brush parsing in this project is referenced and modified from the following open source project:
* **Reference Project**: [Brush-Converter](https://github.com/tohsakrat/Brush-Converter)
* **Open Source License**: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.en) (Attribution-NonCommercial 4.0 International)

**Special Declaration**: In accordance with the requirements of the CC BY-NC 4.0 license, this project is strictly prohibited for any form of commercial use.

