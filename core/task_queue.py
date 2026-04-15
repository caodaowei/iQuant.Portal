"""Celery 任务队列配置"""
from celery import Celery
from config.settings import settings

# 创建 Celery 应用
celery_app = Celery(
    'iquant',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        'core.tasks',
    ]
)

# Celery 配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1小时超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# 任务路由（可选，用于分布式部署）
celery_app.conf.task_routes = {
    'core.tasks.sync_stock_data': {'queue': 'data_sync'},
    'core.tasks.run_backtest': {'queue': 'backtest'},
    'core.tasks.run_ai_diagnosis': {'queue': 'ai_analysis'},
}

if __name__ == '__main__':
    celery_app.start()
