from __future__ import annotations

import json
import os
import re
import shlex
import ssl
import socket
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.header import decode_header
from typing import Optional


SBER_HOST_RE = re.compile(r"(^|\.)sbi\.sberbank\.ru$", re.IGNORECASE)
SBER_LINK_RE = re.compile(
    r"https://sbi\.sberbank\.ru:9443/ic/ufs/scheduled-statements/v1/rest/download/mail/reports/[A-Za-z0-9]+",
    re.IGNORECASE,
)


class SberDownloadError(Exception):
    pass


class SberLinkExpiredError(SberDownloadError):
    pass


class SberTlsError(SberDownloadError):
    pass


class SberDnsError(SberDownloadError):
    pass


class SberTimeoutError(SberDownloadError):
    pass


class SberHttpError(SberDownloadError):
    pass


class SberEmptyBodyError(SberDownloadError):
    pass


@dataclass(slots=True)
class SberDownloadResult:
    url: str
    file_name: str
    content_type: str
    content_length: int
    body: bytes
    tls_fallback_used: bool = False
    http_status: int = 200


def extract_sber_link(text: str) -> Optional[str]:
    if not text:
        return None
    m = SBER_LINK_RE.search(text)
    return m.group(0) if m else None


def _decode_rfc5987_filename(value: str) -> Optional[str]:
    m = re.search(r"filename\*\s*=\s*([^']*)''([^;]+)", value, flags=re.IGNORECASE)
    if not m:
        return None
    charset = (m.group(1) or "utf-8").strip().lower()
    encoded = m.group(2).strip()
    try:
        return urllib.parse.unquote(encoded, encoding=charset, errors="replace")
    except Exception:
        return urllib.parse.unquote(encoded)


def _decode_mime_words(value: str) -> str:
    parts = []
    for chunk, enc in decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            parts.append(chunk)
    return "".join(parts)


def _extract_filename_from_content_disposition(content_disposition: str) -> Optional[str]:
    if not content_disposition:
        return None

    filename_star = _decode_rfc5987_filename(content_disposition)
    if filename_star:
        return os.path.basename(filename_star)

    m = re.search(r'filename\s*=\s*"([^"]+)"', content_disposition, flags=re.IGNORECASE)
    if m:
        raw = m.group(1).strip()
        try:
            decoded = _decode_mime_words(raw)
        except Exception:
            decoded = raw
        return os.path.basename(decoded)

    m = re.search(r"filename\s*=\s*([^;]+)", content_disposition, flags=re.IGNORECASE)
    if m:
        raw = m.group(1).strip().strip('"')
        try:
            decoded = _decode_mime_words(raw)
        except Exception:
            decoded = raw
        return os.path.basename(decoded)

    return None


def _fallback_filename_from_url(url: str) -> str:
    token = url.rstrip("/").split("/")[-1]
    return f"sber_{token}.xlsx"


def _make_ssl_context(
    ca_file: Optional[str] = None,
    insecure_skip_verify: bool = False,
) -> ssl.SSLContext:
    if insecure_skip_verify:
        ctx = ssl._create_unverified_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    if ca_file:
        if not os.path.exists(ca_file):
            raise SberTlsError(f"CA file not found: {ca_file}")
        try:
            return ssl.create_default_context(cafile=ca_file)
        except ssl.SSLError as exc:
            raise SberTlsError(f"Invalid CA bundle: {ca_file}: {exc}") from exc

    return ssl.create_default_context()


def _normalize_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() != "https":
        raise SberDownloadError("Only HTTPS Sber links are supported")
    if not parsed.hostname or not SBER_HOST_RE.search(parsed.hostname):
        raise SberDownloadError("URL is not a Sber download link")
    if parsed.port not in (9443, None):
        raise SberDownloadError("Unexpected Sber port")
    return url


def _is_probably_xlsx(body: bytes) -> bool:
    return len(body) >= 4 and body[:4] == b"PK\x03\x04"


def _read_last_response_headers(raw_header_bytes: bytes) -> dict[str, str]:
    text = raw_header_bytes.decode("iso-8859-1", errors="replace")
    blocks = [b.strip() for b in text.split("\r\n\r\n") if b.strip()]
    if not blocks:
        return {}

    last = blocks[-1]
    headers: dict[str, str] = {}

    for line in last.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        headers[k.strip().lower()] = v.strip()

    status_match = re.search(r"HTTP/\d(?:\.\d)?\s+(\d{3})", last)
    if status_match:
        headers[":status"] = status_match.group(1)

    return headers


def _curl_download(
    url: str,
    *,
    timeout: int,
    ca_file: Optional[str],
    insecure_skip_verify: bool,
    user_agent: str,
) -> SberDownloadResult:
    curl_bin = os.getenv("SBER_CURL_BIN", "curl")

    with tempfile.TemporaryDirectory(prefix="sber_dl_") as tmpdir:
        body_path = os.path.join(tmpdir, "body.bin")
        headers_path = os.path.join(tmpdir, "headers.txt")

        cmd = [
            curl_bin,
            "-sS",
            "-L",
            "--max-redirs",
            "10",
            "--connect-timeout",
            str(timeout),
            "--max-time",
            str(timeout),
            "-A",
            user_agent,
            "-H",
            "Accept: */*",
            "-D",
            headers_path,
            "-o",
            body_path,
            url,
        ]

        if insecure_skip_verify:
            cmd.insert(1, "-k")
        elif ca_file:
            cmd.extend(["--cacert", ca_file])

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            check=False,
        )

        stderr_text = (proc.stderr or b"").decode("utf-8", errors="replace").strip()

        if proc.returncode != 0:
            low = stderr_text.lower()

            if "certificate" in low or "ssl" in low or "tls" in low:
                raise SberTlsError(f"SBER curl TLS error: {stderr_text or proc.returncode}")
            if "timed out" in low or "timeout" in low:
                raise SberTimeoutError(f"SBER curl timeout: {stderr_text or proc.returncode}")
            if "could not resolve host" in low or "name or service not known" in low:
                raise SberDnsError(f"SBER curl DNS error: {stderr_text or proc.returncode}")

            raise SberDownloadError(f"SBER curl failed: {stderr_text or proc.returncode}")

        try:
            with open(headers_path, "rb") as fh:
                headers_raw = fh.read()
        except FileNotFoundError:
            headers_raw = b""

        headers = _read_last_response_headers(headers_raw)
        status = int(headers.get(":status", "0") or "0")

        if status == 410:
            raise SberLinkExpiredError("SBER link expired (410 Gone)")
        if status == 423:
            raise SberHttpError("SBER HTTP error: 423")
        if status and status != 200:
            raise SberHttpError(f"SBER HTTP error: {status}")

        try:
            with open(body_path, "rb") as fh:
                body = fh.read()
        except FileNotFoundError as exc:
            raise SberEmptyBodyError("SBER curl returned no file") from exc

        if not body:
            raise SberEmptyBodyError("SBER curl returned empty body")

        content_type = headers.get("content-type", "").strip()
        content_disposition = headers.get("content-disposition", "").strip()
        content_length_raw = headers.get("content-length", "").strip()

        file_name = _extract_filename_from_content_disposition(content_disposition)
        if not file_name:
            file_name = _fallback_filename_from_url(url)

        try:
            content_length = int(content_length_raw) if content_length_raw else len(body)
        except ValueError:
            content_length = len(body)

        if content_length <= 0 or len(body) <= 0:
            raise SberEmptyBodyError("SBER curl returned empty file")

        return SberDownloadResult(
            url=url,
            file_name=file_name,
            content_type=content_type,
            content_length=len(body),
            body=body,
            tls_fallback_used=True,
            http_status=status or 200,
        )


def download_sber_report(
    url: str,
    *,
    timeout: int = 30,
    ca_file: Optional[str] = None,
    insecure_skip_verify: bool = False,
    user_agent: str = "Mozilla/5.0",
) -> SberDownloadResult:
    """
    Важно:
    - Только GET. HEAD у Sber endpoint ненадежен.
    - 410 -> протухшая ссылка.
    - TLS/423/5xx/timeout -> пробуем fallback через curl.
    """

    safe_url = _normalize_url(url)

    try:
        ctx = _make_ssl_context(ca_file=ca_file, insecure_skip_verify=insecure_skip_verify)

        req = urllib.request.Request(
            safe_url,
            method="GET",
            headers={
                "User-Agent": user_agent,
                "Accept": "*/*",
            },
        )

        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            if status == 410:
                raise SberLinkExpiredError("SBER link expired (410 Gone)")
            if status != 200:
                raise SberHttpError(f"SBER unexpected status: {status}")

            content_type = (resp.headers.get("Content-Type") or "").strip()
            content_length_raw = resp.headers.get("Content-Length")
            content_disposition = resp.headers.get("Content-Disposition") or ""

            body = resp.read()
            if not body:
                raise SberEmptyBodyError("SBER returned empty body")

            file_name = _extract_filename_from_content_disposition(content_disposition)
            if not file_name:
                file_name = _fallback_filename_from_url(safe_url)

            try:
                content_length = int(content_length_raw) if content_length_raw else len(body)
            except ValueError:
                content_length = len(body)

            if content_length <= 0 or len(body) <= 0:
                raise SberEmptyBodyError("SBER returned empty file")

            return SberDownloadResult(
                url=safe_url,
                file_name=file_name,
                content_type=content_type,
                content_length=len(body),
                body=body,
                tls_fallback_used=False,
                http_status=int(status),
            )

    except urllib.error.HTTPError as exc:
        if exc.code == 410:
            raise SberLinkExpiredError("SBER link expired (410 Gone)") from exc
        if exc.code in (423, 500, 502, 503, 504):
            return _curl_download(
                safe_url,
                timeout=timeout,
                ca_file=ca_file,
                insecure_skip_verify=insecure_skip_verify,
                user_agent=user_agent,
            )
        raise SberHttpError(f"SBER HTTP error: {exc.code}") from exc

    except urllib.error.URLError as exc:
        reason = exc.reason

        if isinstance(reason, ssl.SSLCertVerificationError):
            return _curl_download(
                safe_url,
                timeout=timeout,
                ca_file=ca_file,
                insecure_skip_verify=insecure_skip_verify,
                user_agent=user_agent,
            )

        if isinstance(reason, ssl.SSLError):
            return _curl_download(
                safe_url,
                timeout=timeout,
                ca_file=ca_file,
                insecure_skip_verify=insecure_skip_verify,
                user_agent=user_agent,
            )

        if isinstance(reason, socket.gaierror):
            raise SberDnsError(f"SBER DNS error: {reason}") from exc

        if isinstance(reason, TimeoutError):
            return _curl_download(
                safe_url,
                timeout=timeout,
                ca_file=ca_file,
                insecure_skip_verify=insecure_skip_verify,
                user_agent=user_agent,
            )

        return _curl_download(
            safe_url,
            timeout=timeout,
            ca_file=ca_file,
            insecure_skip_verify=insecure_skip_verify,
            user_agent=user_agent,
        )

    except ssl.SSLCertVerificationError:
        return _curl_download(
            safe_url,
            timeout=timeout,
            ca_file=ca_file,
            insecure_skip_verify=insecure_skip_verify,
            user_agent=user_agent,
        )

    except ssl.SSLError:
        return _curl_download(
            safe_url,
            timeout=timeout,
            ca_file=ca_file,
            insecure_skip_verify=insecure_skip_verify,
            user_agent=user_agent,
        )

    except socket.gaierror as exc:
        raise SberDnsError(f"SBER DNS error: {exc}") from exc

    except TimeoutError:
        return _curl_download(
            safe_url,
            timeout=timeout,
            ca_file=ca_file,
            insecure_skip_verify=insecure_skip_verify,
            user_agent=user_agent,
        )


def _cli() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--timeout", type=int, default=int(os.getenv("SBER_DOWNLOAD_TIMEOUT_SECONDS", "30")))
    parser.add_argument("--ca-file", default=(os.getenv("SBER_CA_CERT_PATH") or "").strip() or None)
    parser.add_argument(
        "--insecure-skip-verify",
        action="store_true",
        default=not (os.getenv("SBER_TLS_VERIFY", "true").strip().lower() in {"1", "true", "yes", "on"}),
    )
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    try:
        result = download_sber_report(
            args.url,
            timeout=args.timeout,
            ca_file=args.ca_file,
            insecure_skip_verify=args.insecure_skip_verify,
        )

        if args.out:
            with open(args.out, "wb") as fh:
                fh.write(result.body)

        print(
            json.dumps(
                {
                    "status": "ok",
                    "url": result.url,
                    "file_name": result.file_name,
                    "content_type": result.content_type,
                    "content_length": result.content_length,
                    "tls_fallback_used": result.tls_fallback_used,
                    "http_status": result.http_status,
                    "saved_to": args.out or None,
                    "is_xlsx_zip": _is_probably_xlsx(result.body),
                },
                ensure_ascii=False,
            )
        )
        return 0

    except SberLinkExpiredError as exc:
        print(json.dumps({"status": "expired", "error": str(exc)}, ensure_ascii=False))
        return 10
    except SberTlsError as exc:
        print(json.dumps({"status": "tls_error", "error": str(exc)}, ensure_ascii=False))
        return 11
    except SberDnsError as exc:
        print(json.dumps({"status": "dns_error", "error": str(exc)}, ensure_ascii=False))
        return 12
    except SberTimeoutError as exc:
        print(json.dumps({"status": "timeout", "error": str(exc)}, ensure_ascii=False))
        return 13
    except SberHttpError as exc:
        print(json.dumps({"status": "http_error", "error": str(exc)}, ensure_ascii=False))
        return 14
    except SberDownloadError as exc:
        print(json.dumps({"status": "download_error", "error": str(exc)}, ensure_ascii=False))
        return 15


if __name__ == "__main__":
    raise SystemExit(_cli())