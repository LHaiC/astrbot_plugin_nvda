from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import aiohttp
from datetime import datetime, timedelta
import asyncio
from functools import lru_cache

@register("nvdastock", "LHaiC", "NVDA股票行情查询", "1.0.0")
class NvidiaStockPlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self._session = None
        self._cache = {}  # 新增内存缓存字典
        self._cache_expiry = timedelta(minutes=5)  # 缓存过期时间

    async def initialize(self) -> None:
        """初始化共享HTTP会话"""
        timeout = aiohttp.ClientTimeout(total=10)
        self._session = aiohttp.ClientSession(timeout=timeout)
        logger.info("NVDA Stock Plugin initialized")

    async def _fetch_with_cache(self, ticker: str) -> dict:
        """带缓存的Alpha Vantage数据获取"""
        now = datetime.now()
        
        # 检查缓存是否存在且未过期
        if ticker in self._cache:
            cached_data, timestamp = self._cache[ticker]
            if now - timestamp < self._cache_expiry:
                logger.info(f"使用缓存数据: {ticker}")
                return cached_data
        
        # 缓存不存在或已过期，从API获取
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": ticker,
            "apikey": "YOUR_API_KEY",  # 需替换为实际API key
        }
        
        try:
            async with self._session.get(
                "https://www.alphavantage.co/query",
                params=params,
                raise_for_status=True,
            ) as resp:
                data = await resp.json()
                
                # 检查API限制提示
                if "Note" in data:
                    raise Exception(data["Note"])
                
                # 更新缓存
                self._cache[ticker] = (data, now)
                return data
                
        except Exception as e:
            logger.error(f"AlphaVantage请求失败: {str(e)}")
            raise

    @filter.command("nvda")
    async def nvda_stock(self, event: AstrMessageEvent) -> None:
        """NVDA股票查询（带缓存）"""
        try:
            data = await self._fetch_with_cache("NVDA")
            quote = data["Global Quote"]
            
            response = (
                "=== 英伟达(NVDA)股票行情 ===\n"
                f"当前价: ${float(quote['05. price']):.2f}\n"
                f"今日开盘: ${float(quote['02. open']):.2f}\n"
                f"今日最高: ${float(quote['03. high']):.2f}\n"
                f"今日最低: ${float(quote['04. low']):.2f}\n"
                f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                "数据来源: Alpha Vantage"
            )
            
            yield event.plain_result(response)

        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            yield event.plain_result(f"服务暂不可用: {str(e)}")

    async def terminate(self) -> None:
        """清理资源"""
        if self._session:
            await self._session.close()
        self._cache.clear()  # 清空缓存
        logger.info("NVDA Stock Plugin terminated")