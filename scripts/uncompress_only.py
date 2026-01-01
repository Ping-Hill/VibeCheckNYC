"""
Uncompress the cleaned compressed images (from 70% to 100% quality).
Does NOT upload to S3 - just uncompresses locally.
"""
from pathlib import Path
from PIL import Image
from tqdm import tqdm

# Paths
COMPRESSED_DIR = Path(__file__).parent.parent / "vibecheck_full_output" / "images_compressed"
UNCOMPRESSED_DIR = Path(__file__).parent.parent / "vibecheck_full_output" / "images_uncompressed"

# Create uncompressed directory
UNCOMPRESSED_DIR.mkdir(exist_ok=True)

def uncompress_images():
    """Uncompress all images from 70% to 100% quality."""
    # Get all compressed image files
    image_files = list(COMPRESSED_DIR.glob("*.jpg"))
    print(f"Found {len(image_files)} compressed images (70% quality)")
    print(f"Will uncompress to 100% quality...")
    print(f"Output directory: {UNCOMPRESSED_DIR}")

    success_count = 0
    error_count = 0

    for image_path in tqdm(image_files, desc="Uncompressing images"):
        try:
            # Open compressed image
            img = Image.open(image_path)

            # Save uncompressed version (100% quality)
            output_path = UNCOMPRESSED_DIR / image_path.name
            img.save(output_path, 'JPEG', quality=100, optimize=False)

            success_count += 1

        except Exception as e:
            print(f"\nError processing {image_path.name}: {e}")
            error_count += 1

    print(f"\n✅ Uncompression complete!")
    print(f"   Success: {success_count} images")
    print(f"   Errors: {error_count} images")
    print(f"   Output: {UNCOMPRESSED_DIR}")

if __name__ == "__main__":
    uncompress_images()
