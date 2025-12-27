import os
import json
from datetime import datetime

BASE_DIR = "logs"

LOG_TYPES = [
    "trade",
    "signal",
    "factors",
    "system",
    "error",
    "snapshot",
]


def _ensure_log_dir(log_type):
    """
    确保 logs/<type>/ 目录存在
    """
    path = os.path.join(BASE_DIR, log_type)
    os.makedirs(path, exist_ok=True)
    return path


def _get_log_file(log_type):
    """
    返回 logs/<type>/<type>_YYYY-MM-DD.log
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_dir = _ensure_log_dir(log_type)
    filename = f"{log_type}_{date_str}.log"
    return os.path.join(log_dir, filename)


def _write(log_type, level, message, module=None, extra=None):
    """
    写入结构化日志（JSON 格式）
    """
    log_file = _get_log_file(log_type)

    record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "level": level,
        "module": module or "unknown",
        "message": message,
    }

    if extra:
        record["extra"] = extra

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ============================
#   对外暴露的日志接口
# ============================

def log_trade(message, module="trade", extra=None, print_to_console=True):
    """
    交易日志：同时输出到终端和写入文件
    """
    # 写入文件（结构化 JSON）
    _write("trade", "INFO", message, module, extra)
    
    # 输出到终端（带时间戳）
    if print_to_console:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] 📊 {message}"
        print(formatted)


def log_signal(message, module="signal", extra=None, print_to_console=False):
    """
    信号日志：写入文件，可选输出到终端
    """
    _write("signal", "INFO", message, module, extra)
    if print_to_console:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] 📡 {message}"
        print(formatted)


def log_factors(message, module="factors", extra=None, print_to_console=False):
    """
    因子日志：写入文件，可选输出到终端
    """
    _write("factors", "INFO", message, module, extra)
    if print_to_console:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] 📈 {message}"
        print(formatted)


def log_system(message, module="system", extra=None, print_to_console=False):
    """
    系统日志：写入文件，可选输出到终端
    """
    _write("system", "INFO", message, module, extra)
    if print_to_console:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] 🔧 {message}"
        print(formatted)


def log_error(message, module="error", extra=None, print_to_console=True):
    """
    错误日志：同时输出到终端和写入文件
    """
    # 写入文件（结构化 JSON）
    _write("error", "ERROR", message, module, extra)
    
    # 输出到终端（带时间戳）
    if print_to_console:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] ❌ {message}"
        print(formatted)


def log_snapshot(message, module="snapshot", extra=None, print_to_console=False):
    """
    快照日志：写入文件，可选输出到终端
    """
    _write("snapshot", "INFO", message, module, extra)
    if print_to_console:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] 💾 {message}"
        print(formatted)


# ============================
#   兼容旧系统的日志接口（唯一版本）
# ============================

def write_log(message):
    """
    兼容旧系统的日志函数：
    - 终端打印旧格式（带时间戳）
    - 写入 system_YYYY-MM-DD.log
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"

    # 终端打印旧格式
    print(formatted)

    # 写入系统日志（结构化 JSON）
    _write("system", "INFO", message, module="legacy")