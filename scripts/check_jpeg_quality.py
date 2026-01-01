"""
Check JPEG quality/compression level of images.
Analyzes file size and metadata to estimate quality.
"""
from pathlib import Path
from PIL import Image
import os

IMAGE_DIR = Path(__file__).parent.parent / "vibecheck_full_output" / "images_compressed"

def check_jpeg_quality():
    """Check quality indicators for sample images."""

    # Get first 10 images as samples
    image_files = list(IMAGE_DIR.glob("*.jpg"))[:10]

    print("=" * 80)
    print("JPEG QUALITY CHECK")
    print("=" * 80)
    print(f"\nAnalyzing {len(image_files)} sample images...\n")

    results = []

    for img_path in image_files:
        try:
            # Get file size
            file_size = os.path.getsize(img_path)

            # Open image to get dimensions
            img = Image.open(img_path)
            width, height = img.size
            pixels = width * height

            # Calculate bytes per pixel (indicator of compression)
            # Typical values:
            # - High quality (90-100%): 1.5-3+ bytes/pixel
            # - Medium quality (70-80%): 0.8-1.5 bytes/pixel
            # - Low quality (50-60%): 0.3-0.8 bytes/pixel
            bytes_per_pixel = file_size / pixels

            # Estimate quality
            if bytes_per_pixel > 1.5:
                quality_estimate = "HIGH (90-100%)"
            elif bytes_per_pixel > 0.8:
                quality_estimate = "MEDIUM (70-80%)"
            else:
                quality_estimate = "LOW (50-60%)"

            results.append({
                'filename': img_path.name,
                'size_kb': file_size / 1024,
                'dimensions': f"{width}x{height}",
                'bytes_per_pixel': bytes_per_pixel,
                'quality_estimate': quality_estimate
            })

            img.close()

        except Exception as e:
            print(f"Error analyzing {img_path.name}: {e}")

    # Print results
    print(f"{'Filename':<50} {'Size (KB)':<12} {'Dimensions':<15} {'B/px':<8} {'Quality'}")
    print("-" * 100)

    for r in results:
        print(f"{r['filename']:<50} {r['size_kb']:<12.1f} {r['dimensions']:<15} {r['bytes_per_pixel']:<8.2f} {r['quality_estimate']}")

    # Calculate average
    avg_bpp = sum(r['bytes_per_pixel'] for r in results) / len(results)

    print("\n" + "=" * 80)
    print(f"Average bytes/pixel: {avg_bpp:.2f}")

    if avg_bpp > 1.5:
        print("✅ Images appear to be HIGH QUALITY (90-100%)")
        print("   → Uncompression may not be necessary")
    elif avg_bpp > 0.8:
        print("⚠️  Images appear to be MEDIUM QUALITY (70-80%)")
        print("   → Uncompression to 100% may provide some improvement")
    else:
        print("❌ Images appear to be LOW QUALITY (50-60%)")
        print("   → Uncompression to 100% will help significantly")

    print("=" * 80)

if __name__ == "__main__":
    check_jpeg_quality()
