"""
Upload uncompressed images to S3, replacing the old compressed versions.
Uses the same S3 path: s3://vibecheck-nyc-images/images/
"""
from pathlib import Path
import boto3
from tqdm import tqdm

# Paths
UNCOMPRESSED_DIR = Path(__file__).parent.parent / "vibecheck_full_output" / "images_compressed"
S3_BUCKET = "vibecheck-nyc-images"
S3_PREFIX = "images/"

# Initialize S3 client
s3 = boto3.client('s3')

def upload_to_s3():
    """Upload all uncompressed images to S3, replacing old versions."""
    # Get all uncompressed image files
    image_files = list(UNCOMPRESSED_DIR.glob("*.jpg"))
    print(f"Found {len(image_files)} uncompressed images to upload")
    print(f"Destination: s3://{S3_BUCKET}/{S3_PREFIX}")
    print(f"This will REPLACE the existing compressed images in S3\n")

    success_count = 0
    error_count = 0

    for image_path in tqdm(image_files, desc="Uploading to S3"):
        try:
            # Upload to S3 (will overwrite if exists)
            s3_key = f"{S3_PREFIX}{image_path.name}"
            s3.upload_file(
                str(image_path),
                S3_BUCKET,
                s3_key,
                ExtraArgs={
                    'ContentType': 'image/jpeg',
                    'ACL': 'public-read'
                }
            )
            success_count += 1

        except Exception as e:
            print(f"\nError uploading {image_path.name}: {e}")
            error_count += 1

    print(f"\n✅ S3 Upload complete!")
    print(f"   Success: {success_count} images")
    print(f"   Errors: {error_count} images")
    print(f"   Location: s3://{S3_BUCKET}/{S3_PREFIX}")
    print(f"\nOld compressed images have been replaced with new uncompressed versions.")

if __name__ == "__main__":
    upload_to_s3()
