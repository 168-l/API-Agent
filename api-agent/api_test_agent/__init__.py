"""API 接口自动化测试 Agent - 企业级测试框架"""

__version__ = "1.0.0"
__author__ = "API Test Agent"

from .client import HttpClient
from .test_case import TestCase, TestStep
from .executor import TestExecutor
from .assertions import AssertionEngine
from .variables import VariableManager
from .report_generator import ReportGenerator

__all__ = [
    'HttpClient',
    'TestCase',
    'TestStep',
    'TestExecutor',
    'AssertionEngine',
    'VariableManager',
    'ReportGenerator'
]