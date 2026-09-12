"""图片理解 MCP Server — 提供图片分析、OCR、EXIF 等能力

支持:
- 读取图片并返回给 AI 模型进行视觉分析
- 基础图片信息提取 (尺寸、格式、EXIF)
- OCR 文字识别 (需要 pytesseract)
- 图片元数据分析
"""
import base64
import json
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("image-understanding-server")

# ========== 工具函数 ==========

def _image_to_base64(image_path: str) -> tuple[str, str]:
    """将图片文件转为 base64, 返回 (mime_type, base64_data)"""
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".svg": "image/svg+xml",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }
    mime = mime_map.get(ext, "image/png")
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return mime, data

def _validate_image(path: str) -> str:
    """验证图片文件存在且格式可识别"""
    if not os.path.isfile(path):
        raise ValueError(f"文件不存在: {path}")
    ext = os.path.splitext(path)[1].lower()
    valid = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".tif"}
    if ext not in valid:
        raise ValueError(f"不支持的图片格式: {ext}")
    return path

# ========== Tools ==========

@mcp.tool()
def get_image_info(image_path: str) -> str:
    """获取图片基本信息: 格式、尺寸、文件大小、色彩模式

    Args:
        image_path: 图片文件路径
    """
    _validate_image(image_path)

    try:
        from PIL import Image
    except ImportError:
        return json.dumps({
            "error": "Pillow 未安装。运行: pip install Pillow",
            "file_size": os.path.getsize(image_path),
            "file_name": os.path.basename(image_path),
        }, ensure_ascii=False)

    img = Image.open(image_path)
    info = {
        "file_name": os.path.basename(image_path),
        "format": img.format,
        "mode": img.mode,
        "size": f"{img.width} x {img.height} (像素)",
        "file_size": f"{os.path.getsize(image_path):,} bytes",
        "dpi": img.info.get("dpi", "N/A"),
    }

    # EXIF 信息 (JPEG/TIFF)
    exif_data = {}
    if hasattr(img, "_getexif") and img._getexif():
        from PIL.ExifTags import TAGS
        for tag_id, value in img._getexif().items():
            tag_name = TAGS.get(tag_id, tag_id)
            if isinstance(value, bytes):
                value = value.hex()
            exif_data[tag_name] = str(value)

    if exif_data:
        # 只保留关键字段
        key_fields = ["DateTime", "Make", "Model", "GPSInfo", "Orientation", "Software"]
        key_exif = {k: exif_data[k] for k in key_fields if k in exif_data}
        if key_exif:
            info["exif"] = key_exif

    return json.dumps(info, ensure_ascii=False, indent=2)


@mcp.tool()
def read_image_for_analysis(image_path: str) -> str:
    """读取图片并编码为 base64, 供 AI 模型进行视觉分析时使用。
    与其他工具配合: 先用此工具获取图片数据, AI 模型可直接理解和分析图片内容。

    Args:
        image_path: 图片文件路径
    """
    _validate_image(image_path)
    mime, data = _image_to_base64(image_path)

    # 图片过大则降采样
    max_size = 5 * 1024 * 1024  # 5MB base64 限制
    if len(data) > max_size:
        try:
            from PIL import Image
            img = Image.open(image_path)
            # 降采样到合适尺寸
            factor = (max_size / len(data)) ** 0.5
            new_w = int(img.width * factor)
            new_h = int(img.height * factor)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            import io
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            data = base64.b64encode(buf.getvalue()).decode("ascii")
            mime = "image/jpeg"
        except ImportError:
            pass

    return json.dumps({
        "mime_type": mime,
        "base64_size": len(data),
        "note": "图片数据已就绪, AI 模型可直接基于此 base64 数据进行视觉分析",
        "data": data,
    }, ensure_ascii=False)


@mcp.tool()
def extract_text_ocr(image_path: str, language: str = "chi_sim+eng") -> str:
    """从图片中提取文字 (OCR)

    Args:
        image_path: 图片文件路径
        language: OCR 语言, 默认 chi_sim+eng (中文简体+英文)
                 也可用: eng, jpn, kor, chi_tra
    """
    _validate_image(image_path)

    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return json.dumps({
            "error": "依赖未安装。运行: pip install pytesseract Pillow\n"
                     "还需要安装 tesseract-ocr: apt install tesseract-ocr tesseract-ocr-chi-sim"
        }, ensure_ascii=False)

    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang=language)

    return json.dumps({
        "text": text.strip(),
        "language": language,
        "image_size": f"{img.width}x{img.height}",
    }, ensure_ascii=False)


@mcp.tool()
def compare_images(image_path1: str, image_path2: str) -> str:
    """对比两张图片的基本属性差异 (尺寸、格式、文件大小)

    Args:
        image_path1: 第一张图片路径
        image_path2: 第二张图片路径
    """
    _validate_image(image_path1)
    _validate_image(image_path2)

    info = {}
    for label, path in [("image1", image_path1), ("image2", image_path2)]:
        try:
            from PIL import Image
            img = Image.open(path)
            info[label] = {
                "path": path,
                "format": img.format,
                "mode": img.mode,
                "size": f"{img.width}x{img.height}",
                "file_size": os.path.getsize(path),
            }
        except ImportError:
            info[label] = {
                "path": path,
                "file_size": os.path.getsize(path),
            }

    # 差异分析
    diffs = []
    if "size" in info.get("image1", {}) and "size" in info.get("image2", {}):
        if info["image1"]["size"] != info["image2"]["size"]:
            diffs.append(f"尺寸不同: {info['image1']['size']} vs {info['image2']['size']}")

    s1 = info["image1"]["file_size"]
    s2 = info["image2"]["file_size"]
    if s1 and s2:
        ratio = s2 / s1 if s1 > 0 else 0
        diffs.append(f"文件大小比: image2/image1 = {ratio:.2f}x")

    return json.dumps({
        "image1": info["image1"],
        "image2": info["image2"],
        "differences": diffs or ["无明显差异 (尺寸/格式层面)"],
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def batch_analyze_directory(directory: str, pattern: str = "*") -> str:
    """批量分析目录下的所有图片文件

    Args:
        directory: 目录路径
        pattern: 文件名匹配模式, 如 "*.png" 或 "photo_*"
    """
    if not os.path.isdir(directory):
        return f"错误: 目录不存在 — {directory}"

    import fnmatch
    import glob

    # 查找图片文件
    images = []
    for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]:
        for f in glob.glob(os.path.join(directory, f"*{ext}")):
            name = os.path.basename(f)
            if fnmatch.fnmatch(name, pattern) or pattern == "*":
                images.append(f)

    if not images:
        return f"在 {directory} 中未找到匹配 '{pattern}' 的图片"

    results = []
    for img_path in sorted(images):
        try:
            from PIL import Image
            img = Image.open(img_path)
            results.append({
                "name": os.path.basename(img_path),
                "format": img.format,
                "size": f"{img.width}x{img.height}",
                "file_size": os.path.getsize(img_path),
            })
        except Exception:
            results.append({
                "name": os.path.basename(img_path),
                "file_size": os.path.getsize(img_path),
                "error": "无法打开",
            })

    return json.dumps({
        "total": len(results),
        "directory": directory,
        "images": results[:50],
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def create_thumbnail(image_path: str, max_size: int = 256, output_path: str = "") -> str:
    """生成图片缩略图

    Args:
        image_path: 原图路径
        max_size: 缩略图最大边长 (像素)
        output_path: 输出路径, 默认为原图同目录下 thumb_ 前缀
    """
    _validate_image(image_path)

    try:
        from PIL import Image
    except ImportError:
        return "错误: 需要 Pillow。运行 pip install Pillow"

    img = Image.open(image_path)
    img.thumbnail((max_size, max_size), Image.LANCZOS)

    if not output_path:
        dir_name = os.path.dirname(image_path)
        base = os.path.basename(image_path)
        name, ext = os.path.splitext(base)
        output_path = os.path.join(dir_name, f"thumb_{name}{ext}")

    img.save(output_path)
    return json.dumps({
        "thumbnail_path": output_path,
        "thumbnail_size": f"{img.width}x{img.height}",
        "original_size": f"{Image.open(image_path).width}x{Image.open(image_path).height}",
    }, ensure_ascii=False, indent=2)


# ========== Resources ==========

@mcp.resource("image://supported-formats")
def supported_formats() -> str:
    """列出支持的图片格式和处理能力"""
    capabilities = {
        "formats": ["PNG", "JPEG", "GIF", "WebP", "BMP", "TIFF"],
        "max_base64_size": "5 MB (超过自动降采样)",
        "ocr_languages": ["chi_sim (中文简体)", "chi_tra (中文繁体)", "eng (英文)", "jpn (日文)", "kor (韩文)"],
        "requires": {
            "basic": "Pillow (pip install Pillow)",
            "ocr": "pytesseract + tesseract-ocr (pip install pytesseract; apt install tesseract-ocr)",
        },
    }
    return json.dumps(capabilities, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
