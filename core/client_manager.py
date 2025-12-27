"""
统一的 Binance 客户端管理器（单例模式）
"""
from binance.client import Client
from config.secrets import API_KEY, API_SECRET, USE_TESTNET


class ClientManager:
    """Binance 客户端单例管理器"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ClientManager, cls).__new__(cls)
        return cls._instance
    
    def get_client(self):
        """获取 Binance 客户端实例（单例）"""
        if self._client is None:
            self._client = Client(
                api_key=API_KEY,
                api_secret=API_SECRET,
                testnet=USE_TESTNET
            )
        return self._client
    
    def reset(self):
        """重置客户端（用于测试或重新连接）"""
        self._client = None


# 全局单例实例
_client_manager = ClientManager()


def get_futures_client():
    """
    获取 Binance 期货客户端（统一入口）
    所有模块都应使用此函数获取客户端
    """
    return _client_manager.get_client()

