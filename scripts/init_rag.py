"""一次完成 Milvus Schema、四本原著和三国问答初始化。"""

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.vdb_init_milvus import connect_milvus, create_all_collections
from rag_core.config import get_settings
from rag_core.services.ingestion_service import IngestionService


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化四大名著 RAG")
    parser.add_argument("--schema-only", action="store_true", help="只创建 Schema，不执行入库")
    parser.add_argument("--recreate", action="store_true", help="删除并重建两张 Collection")
    args = parser.parse_args()

    settings = get_settings()
    client = connect_milvus(settings, ensure_database=True)
    result = {
        "schema": create_all_collections(
            client,
            settings=settings,
            recreate=args.recreate,
        )
    }
    if not args.schema_only:
        service = IngestionService(settings, client=client)
        result["documents"] = service.ingest_novels()
        result["qa_pairs"] = service.ingest_qa_pairs()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
