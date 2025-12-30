"""
Uncompress the cleaned compressed images (from 70% to 100% quality) and upload to S3.
This will replace the blurry images currently in S3.
"""
import os
from pathlib import Path
from PIL import Image
import boto3
from tqdm import tqdm

# Paths
COMPRESSED_DIR = Path(__file__).parent.parent / "vibecheck_full_output" / "images_compressed"
S3_BUCKET = "vibecheck-nyc-images"
S3_PREFIX = "images/"

# Initialize S3 client
s3 = boto3.client('s3')

def uncompress_and_upload():
    """Uncompress all images from 70% to 100% quality and upload directly to S3."""
    # Get all compressed image files
    image_files = list(COMPRESSED_DIR.glob("*.jpg"))
    print(f"Found {len(image_files)} compressed images (70% quality)")
    print(f"Will uncompress to 100% quality and upload to S3...")

    success_count = 0
    error_count = 0

    for image_path in tqdm(image_files, desc="Uncompressing and uploading"):
        try:
            # Open compressed image
            img = Image.open(image_path)

            # Create temporary uncompressed version (100% quality)
            temp_path = Path("/tmp") / image_path.name
            img.save(temp_path, 'JPEG', quality=100, optimize=False)

            # Upload to S3
            s3_key = f"{S3_PREFIX}{image_path.name}"
            s3.upload_file(
                str(temp_path),
                S3_BUCKET,
                s3_key,
                ExtraArgs={
                    'ContentType': 'image/jpeg',
                    'ACL': 'public-read'
                }
            )

            # Clean up temp file
            temp_path.unlink()
            success_count += 1

        except Exception as e:
            print(f"\nError processing {image_path.name}: {e}")
            error_count += 1

    print(f"\n✅ Upload complete!")
    print(f"   Success: {success_count} images")
    print(f"   Errors: {error_count} images")
    print(f"   Destination: s3://{S3_BUCKET}/{S3_PREFIX}")

if __name__ == "__main__":
    uncompress_and_upload()
