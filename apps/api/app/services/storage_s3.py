from __future__ import annotations

import os
import hashlib
from dataclasses import dataclass
from typing import Optional, Tuple

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


@dataclass(frozen=True)
class S3ObjectRef:
    bucket: str
    key: str


def _client():
    endpoint = os.getenv("S3_ENDPOINT_URL")
    ak = os.getenv("AWS_ACCESS_KEY_ID")
    sk = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=ak,
        aws_secret_access_key=sk,
        region_name=region,
        config=Config(signature_version="s3v4", retries={"max_attempts": 5, "mode": "standard"}),
    )


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def put_bytes(key: str, data: bytes, content_type: Optional[str] = None) -> S3ObjectRef:
    bucket = os.getenv("S3_BUCKET", "vikki-dev")
    s3 = _client()
    extra = {}
    if content_type:
        extra["ContentType"] = content_type

    s3.put_object(Bucket=bucket, Key=key, Body=data, **extra)
    return S3ObjectRef(bucket=bucket, key=key)


def get_bytes(ref: S3ObjectRef) -> bytes:
    s3 = _client()
    obj = s3.get_object(Bucket=ref.bucket, Key=ref.key)
    return obj["Body"].read()


def ensure_bucket_exists() -> Tuple[bool, str]:
    bucket = os.getenv("S3_BUCKET", "vikki-dev")
    s3 = _client()
    existing = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
    if bucket in existing:
        return False, bucket
    s3.create_bucket(Bucket=bucket)
    return True, bucket