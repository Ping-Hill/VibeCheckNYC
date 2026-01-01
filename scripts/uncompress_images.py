"""
Uncompress images_compressed from 70% to 100% quality.
Overwrites the existing images_compressed folder.
"""
from pathlib import Path
from PIL import Image
from tqdm import tqdm

COMPRESSED_DIR = Path(__file__).parent.parent / "vibecheck_full_output" / "images_compressed"

def uncompress_images():
    """Uncompress all images from 70% to 100% quality."""
    image_files = list(COMPRESSED_DIR.glob("*.jpg"))
    print(f"Found {len(image_files)} images to uncompress")
    print(f"Converting from 70% to 100% quality...")

    success_count = 0
    error_count = 0

    for image_path in tqdm(image_files, desc="Uncompressing"):
        try:
            # Open image
            img = Image.open(image_path)

            # Save at 100% quality (overwrite original)
            img.save(image_path, 'JPEG', quality=100, optimize=False)
            success_count += 1

        except Exception as e:
            print(f"\nError processing {image_path.name}: {e}")
            error_count += 1

    print(f"\n✅ Uncompression complete!")
    print(f"   Success: {success_count} images")
    print(f"   Errors: {error_count} images")

if __name__ == "__main__":
    uncompress_images()
