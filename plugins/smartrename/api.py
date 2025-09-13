from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.core.context import MediaInfo
from app.core.meta import MetaBase
from app.log import logger
from app.schemas import FileItem

router = APIRouter()

# 重命名配置
rename_config = {
    "movie_format": settings.MOVIE_RENAME_FORMAT,
    "tv_format": settings.TV_RENAME_FORMAT
}

# 文件列表
file_list: List[Dict] = []

@router.get("/config")
def get_config():
    """获取重命名配置"""
    return rename_config

@router.post("/config")
def save_config(config: Dict):
    """保存重命名配置"""
    global rename_config
    rename_config = config
    return {"success": True}

@router.get("/files")
def get_files():
    """获取文件列表"""
    return file_list

@router.get("/preview/{file_id}")
def preview_rename(file_id: str):
    """预览重命名结果"""
    try:
        file = next(f for f in file_list if f["id"] == file_id)
        # TODO: 调用重命名预览逻辑
        new_name = "预览文件名"
        return {"newName": new_name}
    except StopIteration:
        raise HTTPException(status_code=404, detail="File not found")

@router.post("/rename/{file_id}")
def execute_rename(file_id: str):
    """执行重命名操作"""
    try:
        file = next(f for f in file_list if f["id"] == file_id)
        # TODO: 调用重命名执行逻辑
        file["status"] = "success"
        return {"success": True}
    except StopIteration:
        raise HTTPException(status_code=404, detail="File not found")

def add_file(file_item: FileItem, mediainfo: MediaInfo, meta: MetaBase) -> None:
    """添加文件到列表"""
    file_list.append({
        "id": str(len(file_list) + 1),
        "originalName": file_item.name,
        "newName": "",
        "status": "pending",
        "mediaInfo": mediainfo.dict(),
        "meta": meta.dict()
    })