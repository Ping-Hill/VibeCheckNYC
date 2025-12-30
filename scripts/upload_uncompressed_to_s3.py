"""
Upload uncompressed images to S3 to replace compressed versions.
"""
import os
import boto3
from pathlib import Path
from tqdm import tqdm

# Paths
IMAGE_DIR = Path(__file__).parent.parent / "vibecheck_full_output" / "images"
S3_BUCKET = "vibecheck-nyc-images"
S3_PREFIX = "images/"

# Initialize S3 client
s3 = boto3.client('s3')

def upload_images():
    """Upload all images to S3."""
    # Get all image files
    image_files = list(IMAGE_DIR.glob("*.jpg"))
    print(f"Found {len(image_files)} images to upload")

    # Upload with progress bar
    for image_path in tqdm(image_files, desc="Uploading images"):
        s3_key = f"{S3_PREFIX}{image_path.name}"

        try:
            # Upload with public-read ACL
            s3.upload_file(
                str(image_path),
                S3_BUCKET,
                s3_key,
                ExtraArgs={
                    'ContentType': 'image/jpeg',
                    'ACL': 'public-read'
                }
            )
        except Exception as e:
            print(f"\nError uploading {image_path.name}: {e}")

    print(f"\n✅ Uploaded {len(image_files)} images to s3://{S3_BUCKET}/{S3_PREFIX}")

if __name__ == "__main__":
    upload_images()
