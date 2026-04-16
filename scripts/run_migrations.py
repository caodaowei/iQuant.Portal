#!/usr/bin/env python3
"""执行数据库迁移脚本"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from loguru import logger
from core.database import db

def run_migrations():
    """执行所有数据库迁移"""
    logger.info("开始执行数据库迁移...")
    
    migration_dir = Path(__file__).parent.parent / "db" / "migrations"
    migration_files = sorted(migration_dir.glob("*.sql"))
    
    for migration_file in migration_files:
        logger.info(f"执行迁移文件: {migration_file.name}")
        try:
            with open(migration_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 执行SQL语句，按分号分割
            statements = sql_content.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement:
                    db.execute(statement)
            
            logger.info(f"✅ 成功执行: {migration_file.name}")
        except Exception as e:
            logger.error(f"❌ 执行迁移文件 {migration_file.name} 失败: {e}")
            return False
    
    logger.info("所有数据库迁移执行完成!")
    return True

if __name__ == "__main__":
    success = run_migrations()
    if success:
        logger.info("数据库迁移成功完成")
        sys.exit(0)
    else:
        logger.error("数据库迁移失败")
        sys.exit(1)