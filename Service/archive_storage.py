"""档案文件存储适配器；生产可替换为对象存储实现。"""

from pathlib import Path


class LocalArchiveStorage:
    def __init__(self, root: Path | str):
        self.root = Path(root)

    def save(self, content: bytes, object_key: str) -> str:
        target = self.root / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError("档案版本文件已存在，禁止覆盖")
        target.write_bytes(content)
        return object_key

    def read(self, object_key: str) -> bytes:
        return (self.root / object_key).read_bytes()
