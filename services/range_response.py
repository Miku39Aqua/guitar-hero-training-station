"""支持 Range 头的文件下载响应。"""
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse


def ranged_file_response(
    request: Request,
    file_path: Path,
    filename: str,
    media_type: str = "application/zip",
):
    """返回支持断点续传的文件响应。"""
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")
    start, end = 0, file_size - 1

    if range_header:
        try:
            h = range_header.replace("bytes=", "").split("-")
            start = int(h[0]) if h[0] else 0
            end = int(h[1]) if h[1] else file_size - 1
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Range header") from exc

    def file_iterator():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = f.read(min(8192, remaining))
                if not chunk:
                    break
                yield chunk
                remaining -= len(chunk)

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Accept-Ranges": "bytes",
    }
    if range_header:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        headers["Content-Length"] = str(end - start + 1)
        return StreamingResponse(
            file_iterator(), status_code=206, headers=headers, media_type=media_type
        )

    headers["Content-Length"] = str(file_size)
    return StreamingResponse(file_iterator(), status_code=200, headers=headers, media_type=media_type)
