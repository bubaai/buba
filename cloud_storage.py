"""
cloud_storage.py
------------------
Tayyor videoni Cloudflare R2'ga yuklab, ochiq (public) URL qaytaradi.
Instagram API videoni faqat ommaviy URL orqali qabul qilgani uchun bu
qadam publish qilishdan oldin shart.

Nega R2: Amazon S3 bilan to'liq mos (S3 API), lekin trafik chiqishi
(egress) uchun to'lov olinmaydi — video kabi katta fayllar uchun arzon.

Talab qilinadigan environment o'zgaruvchilar:
    R2_ACCOUNT_ID        — Cloudflare account ID
    R2_ACCESS_KEY_ID     — R2 API token (Access Key ID)
    R2_SECRET_ACCESS_KEY — R2 API token (Secret Access Key)
    R2_BUCKET_NAME       — bucket nomi
    R2_PUBLIC_BASE_URL   — ochiq domen, masalan:
                            https://pub-xxxxx.r2.dev
                            yoki o'zingizning custom domeningiz

Sozlash qadamlari:
    1. https://dash.cloudflare.com → R2 → Create bucket
    2. Bucket → Settings → Public Access → yoqish (r2.dev domen beriladi,
       yoki o'z domeningizni ulashingiz mumkin)
    3. R2 → Manage API Tokens → yangi token yarating (Object Read & Write)
"""

import os
import mimetypes
import boto3


def _get_client_and_config():
    account_id = os.environ.get("R2_ACCOUNT_ID")
    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")
    bucket = os.environ.get("R2_BUCKET_NAME")
    public_base_url = os.environ.get("R2_PUBLIC_BASE_URL")

    missing = [
        name
        for name, val in [
            ("R2_ACCOUNT_ID", account_id),
            ("R2_ACCESS_KEY_ID", access_key),
            ("R2_SECRET_ACCESS_KEY", secret_key),
            ("R2_BUCKET_NAME", bucket),
            ("R2_PUBLIC_BASE_URL", public_base_url),
        ]
        if not val
    ]
    if missing:
        raise EnvironmentError(
            f"Quyidagi environment o'zgaruvchilar yo'q: {', '.join(missing)}"
        )

    client = boto3.client(
        service_name="s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    return client, bucket, public_base_url


def upload_video(local_path: str, remote_key: str | None = None) -> str:
    """
    Videoni R2'ga yuklaydi va ochiq URL qaytaradi.

    remote_key berilmasa, fayl nomining o'zi ishlatiladi (masalan
    "videos/mening_reelsim.mp4" kabi papka bilan ham berish mumkin).
    """
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Fayl topilmadi: {local_path}")

    client, bucket, public_base_url = _get_client_and_config()

    if remote_key is None:
        remote_key = os.path.basename(local_path)

    content_type, _ = mimetypes.guess_type(local_path)
    extra_args = {"ContentType": content_type} if content_type else {}

    client.upload_file(local_path, bucket, remote_key, ExtraArgs=extra_args)

    public_url = f"{public_base_url.rstrip('/')}/{remote_key}"
    return public_url


def delete_video(remote_key: str) -> None:
    """R2'dan faylni o'chiradi (Instagram joylashdan keyin tozalash uchun, ixtiyoriy)."""
    client, bucket, _ = _get_client_and_config()
    client.delete_object(Bucket=bucket, Key=remote_key)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Ishlatish: python cloud_storage.py <video.mp4>")
        sys.exit(1)

    url = upload_video(sys.argv[1])
    print(f"Ochiq URL: {url}")
