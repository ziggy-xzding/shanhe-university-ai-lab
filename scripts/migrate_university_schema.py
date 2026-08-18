"""创建高校模块新增表；该脚本不删除或迁移既有业务数据。"""

from DAO.db import Base, engine
import Model.university_tables  # noqa: F401 - 注册 ORM 表


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("高校模块新增表和索引已检查完成。")


if __name__ == "__main__":
    main()
