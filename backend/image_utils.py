import os
import hashlib
import re
from datetime import datetime
from PIL import Image
import rasterio
import numpy as np
import io
import base64
from typing import Optional


def parse_date_from_filename(filename_or_path: str) -> tuple:
    """Parse date from a filename (or full path). Return a sortable tuple (year, month_num, day)."""
    try:
        filename = os.path.basename(filename_or_path)
    except Exception:
        filename = str(filename_or_path)
    filename_lower = filename.lower()
    
    # Try the new enhanced dataset format: YYYY_MM_DD.png
    enhanced_pattern = r'^(\d{4})_(\d{1,2})_(\d{1,2})\.png$'
    match = re.search(enhanced_pattern, filename_lower)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return (year, month, day)
    
    # Month name mapping
    month_map = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'sept': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }
    
    # Try different legacy patterns
    patterns = [
        r'([a-z]+)_(\d{4})',
        r'(\d+)([a-z]+),(\d{4})',
        r'(\d+)([a-z]+)(\d{4})',
        r'([a-z]+)(\d+)_(\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename_lower)
        if match:
            groups = match.groups()
            
            if len(groups) == 2:
                month_str, year_str = groups
                if month_str in month_map:
                    return (int(year_str), month_map[month_str], 1)
                    
            elif len(groups) == 3:
                if groups[0].isdigit():
                    day_str, month_str, year_str = groups
                    if month_str in month_map:
                        return (int(year_str), month_map[month_str], int(day_str))
                else:
                    month_str, day_str, year_str = groups
                    if month_str in month_map:
                        return (int(year_str), month_map[month_str], int(day_str))
    
    # Try to extract year at least
    year_match = re.search(r'20\d{2}', filename)
    if year_match:
        year = int(year_match.group())
        return (year, 0, 0)

    # Last resort: use file modification time
    try:
        if os.path.exists(filename_or_path):
            mtime = os.path.getmtime(filename_or_path)
            dt = datetime.fromtimestamp(mtime)
            return (dt.year, dt.month, dt.day)
    except Exception:
        pass

    return (2024, 0, 0)


def make_thumbnail(source_path: str, width: int = 300, height: int = 300) -> Optional[str]:
    """
    Generate (and cache) a thumbnail for `source_path` with the requested size.
    Returns the filesystem path to the thumbnail image, or None on failure.
    Handles multispectral TIFF files using rasterio.
    """
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    THUMB_CACHE_DIR = os.path.join(ROOT_DIR, 'thumbnail_cache')
    os.makedirs(THUMB_CACHE_DIR, exist_ok=True)
    
    if not os.path.isfile(source_path):
        return None

    # Deterministic cache name that includes size
    base_h = hashlib.sha256(source_path.encode('utf-8')).hexdigest()
    thumb_name = f"{base_h}_{width}x{height}.png"
    thumb_path = os.path.join(THUMB_CACHE_DIR, thumb_name)

    if os.path.isfile(thumb_path):
        return thumb_path

    try:
        # Check if it's a TIFF file that might need special handling
        if source_path.lower().endswith(('.tif', '.tiff')):
            # First, try using rasterio for multispectral/complex TIFFs
            try:
                with rasterio.open(source_path) as src:
                    # Read the data
                    data = src.read()
                    
                    # Handle different band counts
                    if data.shape[0] >= 3:
                        # Multi-band: Use first 3 bands as RGB
                        if data.shape[0] >= 4:
                            # For 4+ bands, try to pick RGB-like bands
                            rgb = np.stack([
                                data[2, :, :],  # Red
                                data[1, :, :],  # Green
                                data[0, :, :]   # Blue
                            ], axis=-1)
                        else:
                            # 3 bands: assume RGB
                            rgb = np.stack([
                                data[0, :, :],
                                data[1, :, :],
                                data[2, :, :]
                            ], axis=-1)
                    elif data.shape[0] == 1:
                        # Single band: grayscale
                        rgb = data[0, :, :]
                    else:
                        raise ValueError(f"Unsupported band count: {data.shape[0]}")
                    
                    # Normalize to 0-255 range
                    if rgb.dtype in [np.float32, np.float64]:
                        rgb_min, rgb_max = rgb.min(), rgb.max()
                        if rgb_max > rgb_min:
                            rgb = ((rgb - rgb_min) / (rgb_max - rgb_min) * 255).astype(np.uint8)
                        else:
                            rgb = np.zeros_like(rgb, dtype=np.uint8)
                    elif rgb.dtype == np.uint16:
                        rgb_min, rgb_max = rgb.min(), rgb.max()
                        if rgb_max > rgb_min:
                            rgb = ((rgb.astype(np.float32) - rgb_min) / (rgb_max - rgb_min) * 255).astype(np.uint8)
                        else:
                            rgb = np.zeros_like(rgb, dtype=np.uint8)
                    elif rgb.dtype != np.uint8:
                        rgb_min, rgb_max = rgb.min(), rgb.max()
                        if rgb_max > rgb_min:
                            rgb = ((rgb.astype(np.float32) - rgb_min) / (rgb_max - rgb_min) * 255).astype(np.uint8)
                        else:
                            rgb = np.zeros_like(rgb, dtype=np.uint8)
                    
                    # Create PIL Image
                    if len(rgb.shape) == 3:
                        im = Image.fromarray(rgb, mode='RGB')
                    else:
                        im = Image.fromarray(rgb, mode='L').convert('RGB')
                    
                    # Create thumbnail
                    im.thumbnail((width, height), Image.LANCZOS)
                    im.save(thumb_path, format='PNG', optimize=True)
                    
                    return thumb_path
                    
            except Exception as e:
                # Fall back to PIL for simpler TIFFs
                try:
                    with Image.open(source_path) as im:
                        im.seek(0)
                        
                        # Convert to RGB mode
                        if im.mode in ('RGB', 'RGBA'):
                            im = im.convert('RGB')
                        elif im.mode == 'L':
                            im = im.convert('RGB')
                        elif im.mode in ('I', 'I;16', 'I;16B', 'I;16L', 'I;16N'):
                            arr = np.array(im, dtype=np.float32)
                            arr_min, arr_max = arr.min(), arr.max()
                            if arr_max > arr_min:
                                arr = ((arr - arr_min) / (arr_max - arr_min) * 255).astype(np.uint8)
                            else:
                                arr = np.zeros_like(arr, dtype=np.uint8)
                            im = Image.fromarray(arr, mode='L').convert('RGB')
                        elif im.mode == 'F':
                            arr = np.array(im)
                            arr_min, arr_max = arr.min(), arr.max()
                            if arr_max > arr_min:
                                arr = ((arr - arr_min) / (arr_max - arr_min) * 255).astype(np.uint8)
                            else:
                                arr = np.zeros_like(arr, dtype=np.uint8)
                            im = Image.fromarray(arr, mode='L').convert('RGB')
                        else:
                            im = im.convert('RGB')
                        
                        # Create thumbnail
                        im.thumbnail((width, height), Image.LANCZOS)
                        im.save(thumb_path, format='PNG', optimize=True)
                        
                    return thumb_path
                except Exception:
                    return None
        else:
            # Standard image processing for PNG, JPG, etc.
            with Image.open(source_path) as im:
                im = im.convert('RGB')
                im.thumbnail((width, height), Image.LANCZOS)
                im.save(thumb_path, format='PNG', optimize=True)
            return thumb_path
    except Exception:
        return None


class ImageProcessor:
    def __init__(self, farm_dataset_dir, thumbnails_dir=None):
        self.farm_dataset_dir = farm_dataset_dir
        # thumbnails_dir is no longer needed since we generate on-the-fly
        
    def generate_thumbnail_base64(self, img_path, size=(500, 500)):
        """
        Generate high-resolution thumbnail in memory and return as base64 string
        Handles both TIFF (legacy) and PNG (enhanced dataset) files
        
        Args:
            img_path (str): Path to the original TIFF or PNG file
            size (tuple): Thumbnail size (width, height)
        
        Returns:
            str: Base64 encoded PNG image, or None if failed
        """
        try:
            # Check if it's a PNG file (enhanced dataset)
            if img_path.lower().endswith('.png'):
                # PNG files are already processed and optimized
                with Image.open(img_path) as img:
                    # Resize if needed
                    if img.size != size:
                        img = img.resize(size, Image.Resampling.LANCZOS)
                    
                    # Convert to base64
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG', optimize=True)
                    buffer.seek(0)
                    
                    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
                    return f"data:image/png;base64,{img_base64}"
            
            # Legacy TIFF processing
            with rasterio.open(img_path) as src:
                bands = src.read()
                
                if bands.shape[0] >= 4:
                    # Create RGB image with:
                    # R = band 4 (Red channel)
                    # G = band 3 (Green channel) 
                    # B = band 2 (Blue channel)
                    # Band indexing: rasterio uses 0-based, so band 4=index 3, band 3=index 2, band 2=index 1
                    rgb_composite = np.stack([bands[3], bands[2], bands[1]], axis=-1)  # R, G, B
                    
                    # Check for invalid values
                    if np.any(np.isnan(rgb_composite)) or np.any(np.isinf(rgb_composite)):
                        # Replace NaN/Inf with 0
                        rgb_composite = np.nan_to_num(rgb_composite, nan=0.0, posinf=0.0, neginf=0.0)
                    
                    # Apply aggressive contrast stretching (same as test.py)
                    def aggressive_stretch(rgb_array, percentile_range=(0.5, 99.5)):
                        result = np.zeros_like(rgb_array, dtype=np.float64)
                        for i in range(3):
                            band = rgb_array[:, :, i].astype(np.float64)
                            non_zero = band[band > 0]
                            if len(non_zero) > 0:
                                p_low, p_high = np.percentile(non_zero, percentile_range)
                            else:
                                p_low, p_high = np.percentile(band, percentile_range)
                            if p_high > p_low:
                                result[:, :, i] = (band - p_low) / (p_high - p_low)
                            else:
                                result[:, :, i] = band / np.max(band) if np.max(band) > 0 else band
                        return np.clip(result * 255, 0, 255).astype(np.uint8)
                    
                    # Apply the aggressive stretch
                    rgb_composite = aggressive_stretch(rgb_composite)
                    
                    # Create PIL image
                    img = Image.fromarray(rgb_composite)
                    
                    # Resize to target size (upscale if needed)
                    img = img.resize(size, Image.Resampling.LANCZOS)
                    
                    # Save to memory buffer instead of file
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG', optimize=False, compress_level=1)
                    buffer.seek(0)
                    
                    # Convert to base64 for web display
                    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    
                    return f"data:image/png;base64,{img_base64}"
                    
                else:
                    return None
                    
        except Exception as e:
            return None
    
    def cleanup_thumbnails(self, keep_farms=None):
        """
        No longer needed - thumbnails are generated on-demand and not saved
        """
        pass
    
    def get_thumbnail_stats(self):
        """Get statistics about generated thumbnails - now always zero since not saved"""
        return {'total': 0, 'size_mb': 0, 'note': 'Thumbnails generated on-demand, not saved'}