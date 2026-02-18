import io
from PIL import Image

def process_to_square_jpg(raw_data, size=600, quality=80):
    """Crops 16:9 to 1:1 and resizes to standard JPEG."""
    if not raw_data or len(raw_data) < 100: # Check if data is too small to be an image
        return None
    try:
        img = Image.open(io.BytesIO(raw_data))

        # 1. Convert to RGB (removes transparency/PNG issues)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # 2. Center Crop to Square
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim) / 2
        top = (height - min_dim) / 2
        right = (width + min_dim) / 2
        bottom = (height + min_dim) / 2
        img = img.crop((left, top, right, bottom))

        # 3. Resize
        img = img.resize((size, size), Image.Resampling.LANCZOS)

        # 4. Export as Bytes
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality)
        return output.getvalue()
    except Exception as e:
        print(f"   - [ImageProcessor] Error: {e}")
        return None
