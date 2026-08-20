"""测试音频管线：上传音频 → transcribe → alphaTex"""
import urllib.request
import urllib.parse
import io

# 构造一个假 wav 文件（44 字节最小 wav header + 1 字节数据）
wav_header = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
wav_data = wav_header + b"\x00" * 100

boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="test.wav"\r\n'
    f"Content-Type: audio/wav\r\n\r\n"
).encode() + wav_data + f"\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(
    "http://localhost:8000/api/upload",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST",
)

try:
    resp = urllib.request.urlopen(req, timeout=30)
    print(resp.read().decode())
except Exception as e:
    print(f"失败: {e}")
