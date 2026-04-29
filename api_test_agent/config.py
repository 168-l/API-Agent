import os
import yaml
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class TestConfig:
    """测试配置类"""
    
    base_url: str = ""
    timeout: int = 30
    retries: int = 3
    retry_delay: float = 1.0
    
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    
    variables: Dict[str, Any] = field(default_factory=dict)
    environment: str = "test"
    
    output_dir: str = "./reports"
    log_level: str = "INFO"
    
    concurrent: int = 5
    fail_fast: bool = False
    
    verify_ssl: bool = True
    redirect: bool = True
    
    def __post_init__(self):
        if not self.headers:
            self.headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
    
    @classmethod
    def from_yaml(cls, file_path: str) -> 'TestConfig':
        """从 YAML 文件加载配置"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls(**data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestConfig':
        """从字典创建配置"""
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'base_url': self.base_url,
            'timeout': self.timeout,
            'retries': self.retries,
            'retry_delay': self.retry_delay,
            'headers': self.headers,
            'cookies': self.cookies,
            'variables': self.variables,
            'environment': self.environment,
            'output_dir': self.output_dir,
            'log_level': self.log_level,
            'concurrent': self.concurrent,
            'fail_fast': self.fail_fast,
            'verify_ssl': self.verify_ssl,
            'redirect': self.redirect
        }


def load_config(config_path: Optional[str] = None) -> TestConfig:
    """加载配置文件"""
    default_config = TestConfig()
    
    if config_path and os.path.exists(config_path):
        return TestConfig.from_yaml(config_path)
    
    return default_config