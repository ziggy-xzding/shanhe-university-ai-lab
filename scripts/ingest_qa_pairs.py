"""校验并把 50 条三国问答写入 Milvus。"""

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag_core.services.ingestion_service import DEFAULT_QA_PATH, IngestionService


def main() -> int:
    parser = argparse.ArgumentParser(description="将三国问答数据写入 Milvus")
    parser.add_argument("--path", type=Path, default=DEFAULT_QA_PATH)
    parser.add_argument("--recreate", action="store_true", help="删除并重建问答 Collection")
    args = parser.parse_args()
    result = IngestionService().ingest_qa_pairs(args.path, recreate=args.recreate)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
