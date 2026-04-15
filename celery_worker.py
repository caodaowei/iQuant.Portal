"""Celery Worker 启动脚本

使用方法:
    python celery_worker.py worker --loglevel=info

或者使用命令行:
    celery -A core.task_queue worker --loglevel=info --concurrency=4
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.task_queue import celery_app

if __name__ == '__main__':
    argv = ['worker']

    # 添加命令行参数
    if len(sys.argv) > 1:
        argv.extend(sys.argv[1:])
    else:
        # 默认参数
        argv.extend([
            '--loglevel=info',
            '--concurrency=4',
            '--pool=prefork',
        ])

    celery_app.start(argv)
