from io import BytesIO
from pathlib import Path

from app.config.settings import get_settings
from app.schemas.response import UnifiedResponse
from app.services.KnowledgeBase_md5_service import KnowledgeBaseService


async def _extract_text(content: bytes, suffix: str) -> str:
    """根据文件后缀提取纯文本内容"""
    if suffix in (".txt", ".md"):
        return content.decode("utf-8", errors="ignore")

    if suffix == ".pdf":
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(BytesIO(content))
            return "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )
        except ImportError:
            raise RuntimeError("PDF 解析需要安装 PyPDF2 库")

    if suffix == ".docx":
        try:
            from docx import Document
            doc = Document(BytesIO(content))
            return "\n".join(
                para.text for para in doc.paragraphs if para.text.strip()
            )
        except ImportError:
            raise RuntimeError("DOCX 解析需要安装 python-docx 库")

    raise ValueError(f"不支持的文件格式: {suffix}")


async def upload_documents(content: bytes, filename: str | None) -> UnifiedResponse:
    """上传文件处理：校验 -> 解析 -> 向量化存储"""
    if not filename:
        return UnifiedResponse(code=400, message="文件名不能为空")

    settings = get_settings()
    path = Path(filename)
    suffix = path.suffix.lower()

    # 校验文件大小（MAX_FILE_SIZE 单位是 MB）
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > settings.MAX_FILE_SIZE:
        return UnifiedResponse(
            code=413,
            message=f"文件大小 {file_size_mb:.2f}MB 超过限制 {settings.MAX_FILE_SIZE}MB",
            data={"filename": filename}
        )

    # 校验文件后缀
    if suffix not in settings.ALLOWED_SUFFIXES:
        return UnifiedResponse(
            code=400,
            message=f"[Error] {filename} 暂时不支持上传，仅支持 {settings.ALLOWED_SUFFIXES}"
        )

    # 解析文件成字符串
    try:
        text = await _extract_text(content, suffix)
    except Exception as e:
        return UnifiedResponse(code=400, message=f"文件解析失败: {str(e)}")

    if not text.strip():
        return UnifiedResponse(code=400, message="文件内容为空，无法上传")

    # 向量化存储
    kb_service = KnowledgeBaseService()
    result = kb_service.upload_by_str(text, filename)

    return UnifiedResponse(
        code=200,
        message=f"文件 {filename} 上传成功",
        data=result.data if hasattr(result, "data") else result
    )
