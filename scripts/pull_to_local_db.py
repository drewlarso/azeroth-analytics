from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import boto3
import os


def download_file(s3_client, bucket: str, obj: dict) -> tuple[str, str]:
    key = obj["Key"]
    remote_modified = obj["LastModified"]
    remote_size = obj["Size"]

    os.makedirs(os.path.dirname(key), exist_ok=True)

    if os.path.exists(key):
        local_size = os.path.getsize(key)
        local_modified = os.path.getmtime(key)
        if local_size == remote_size and local_modified >= remote_modified.timestamp():
            return ("skipped", key)

    s3_client.download_file(bucket, key, key)
    return ("downloaded", key)


def sync_r2_to_local(s3_client, bucket: str, max_workers: int = 10):
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket)

    all_objects = [obj for page in pages for obj in page.get("Contents", [])]

    downloaded = 0
    skipped = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(download_file, s3_client, bucket, obj): obj
            for obj in all_objects
        }
        for future in as_completed(futures):
            status, key = future.result()
            if status == "downloaded":
                print(f"[download] {key}")
                downloaded += 1
            else:
                print(f"[skip] {key}")
                skipped += 1

    print(f"\nDone. Downloaded: {downloaded}, Skipped: {skipped}")


if __name__ == "__main__":
    load_dotenv()

    R2_ID = os.getenv("R2_ACCESS_KEY_ID") or ""
    R2_SECRET = os.getenv("R2_SECRET_ACCESS_KEY") or ""
    R2_URL = os.getenv("R2_ENDPOINT_URL") or ""
    R2_BUCKET = os.getenv("R2_BUCKET_NAME") or ""

    s3_client = boto3.client(
        "s3",
        endpoint_url=R2_URL,
        aws_access_key_id=R2_ID,
        aws_secret_access_key=R2_SECRET,
        region_name="auto",
    )

    # The bucket has one folder at the root called "data", so we can pull that directly into the project directory
    sync_r2_to_local(s3_client, R2_BUCKET)
