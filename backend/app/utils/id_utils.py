from __future__ import annotations

from uuid import uuid4
from threading import Lock


class IdGenerator:
    """生成跨进程重启仍唯一的业务 ID。

    之前的实现基于进程内自增计数器，适合纯内存仓储；
    但接入 Milvus 这类持久化存储后，服务重启会让计数重新从 1 开始，
    导致 `app_001`、`ver_001` 这类 ID 与历史数据冲突。
    这里改成带前缀的短 UUID，避免本地联调和线上持久化场景互相打架。
    """

    def __init__(self) -> None:
        self._lock = Lock()

    def next_id(self, prefix: str) -> str:
        with self._lock:
            value = uuid4().hex[:12]
        return f"{prefix}_{value}"

    def reset(self) -> None:
        # 兼容测试夹具保留该方法。UUID 方案没有进程内计数状态可清空。
        return None


id_generator = IdGenerator()
