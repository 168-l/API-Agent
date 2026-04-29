import requests
import time
import json
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)


@dataclass
class Response:
    """响应对象"""
    status_code: int
    headers: Dict[str, str]
    body: Any
    elapsed: float
    cookies: Dict[str, str]
    
    def json(self) -> Any:
        if isinstance(self.body, dict):
            return self.body
        try:
            return json.loads(self.body)
        except:
            return self.body
    
    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


@dataclass
class RequestResult:
    """请求结果"""
    success: bool
    request: Dict[str, Any]
    response: Optional[Response]
    error: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


class HttpClient:
    """HTTP 客户端封装"""
    
    def __init__(
        self,
        base_url: str = "",
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        verify_ssl: bool = True,
        redirect: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.verify_ssl = verify_ssl
        self.redirect = redirect
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(self.headers)
        
        if not redirect:
            self.session.max_redirects = 0
        
        logger.info(f"HTTP客户端初始化完成 - Base URL: {base_url}")
    
    def _build_url(self, path: str) -> str:
        """构建完整 URL"""
        if path.startswith(('http://', 'https://')):
            return path
        return urljoin(f"{self.base_url}/", path.lstrip('/'))
    
    def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> RequestResult:
        """发送 HTTP 请求"""
        start_time = time.time()
        
        method = method.upper()
        full_url = self._build_url(url)
        
        request_info = {
            'method': method,
            'url': full_url,
            **{k: v for k, v in kwargs.items() if k != 'timeout'}
        }
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"尝试 {attempt + 1}/{self.max_retries}: {method} {full_url}")
                
                response = self.session.request(
                    method=method,
                    url=full_url,
                    timeout=self.timeout,
                    cookies=self.cookies,
                    **kwargs
                )
                
                end_time = time.time()
                
                result_response = Response(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    body=self._parse_body(response),
                    elapsed=response.elapsed.total_seconds(),
                    cookies=dict(response.cookies)
                )
                
                return RequestResult(
                    success=True,
                    request=request_info,
                    response=result_response,
                    start_time=start_time,
                    end_time=end_time
                )
                
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {last_error}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        
        end_time = time.time()
        return RequestResult(
            success=False,
            request=request_info,
            response=None,
            error=f"重试 {self.max_retries} 次后仍然失败: {last_error}",
            start_time=start_time,
            end_time=end_time
        )
    
    def _parse_body(self, response: requests.Response) -> Any:
        """解析响应体"""
        content_type = response.headers.get('Content-Type', '')
        
        if 'json' in content_type:
            try:
                return response.json()
            except:
                return response.text
        elif 'xml' in content_type:
            return response.text
        else:
            return response.text
    
    def get(self, url: str, params: Optional[Dict] = None, **kwargs) -> RequestResult:
        """GET 请求"""
        return self._make_request('GET', url, params=params, **kwargs)
    
    def post(self, url: str, data: Any = None, json: Any = None, **kwargs) -> RequestResult:
        """POST 请求"""
        return self._make_request('POST', url, data=data, json=json, **kwargs)
    
    def put(self, url: str, data: Any = None, json: Any = None, **kwargs) -> RequestResult:
        """PUT 请求"""
        return self._make_request('PUT', url, data=data, json=json, **kwargs)
    
    def delete(self, url: str, **kwargs) -> RequestResult:
        """DELETE 请求"""
        return self._make_request('DELETE', url, **kwargs)
    
    def patch(self, url: str, data: Any = None, json: Any = None, **kwargs) -> RequestResult:
        """PATCH 请求"""
        return self._make_request('PATCH', url, data=data, json=json, **kwargs)
    
    def head(self, url: str, **kwargs) -> RequestResult:
        """HEAD 请求"""
        return self._make_request('HEAD', url, **kwargs)
    
    def options(self, url: str, **kwargs) -> RequestResult:
        """OPTIONS 请求"""
        return self._make_request('OPTIONS', url, **kwargs)
    
    def request(self, method: str, url: str, **kwargs) -> RequestResult:
        """通用请求方法"""
        return self._make_request(method, url, **kwargs)
    
    def set_header(self, key: str, value: str):
        """设置请求头"""
        self.headers[key] = value
        self.session.headers[key] = value
    
    def set_cookie(self, key: str, value: str):
        """设置 Cookie"""
        self.cookies[key] = value
    
    def update_headers(self, headers: Dict[str, str]):
        """批量更新请求头"""
        self.headers.update(headers)
        self.session.headers.update(headers)
    
    def close(self):
        """关闭会话"""
        self.session.close()
        logger.info("HTTP 会话已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()