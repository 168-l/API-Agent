import time
import copy
import traceback
import threading
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from queue import Queue
import logging

from .client import HttpClient, RequestResult
from .test_case import TestCase, TestStep, TestStatus, TestSuite
from .assertions import AssertionEngine, AssertionResult
from .variables import VariableManager
from .config import TestConfig

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """步骤执行结果"""
    step_name: str
    status: TestStatus
    request_result: Optional[RequestResult] = None
    assertion_results: List[AssertionResult] = None
    extracted_variables: Dict[str, Any] = None
    error_message: str = ""
    start_time: datetime = None
    end_time: datetime = None
    duration: float = 0.0
    
    @property
    def success(self) -> bool:
        return self.status == TestStatus.PASSED


@dataclass
class TestCaseResult:
    """测试用例执行结果"""
    test_case_name: str
    status: TestStatus
    step_results: List[StepResult] = None
    total_duration: float = 0.0
    error_message: str = ""
    start_time: datetime = None
    end_time: datetime = None
    
    @property
    def passed(self) -> bool:
        return self.status == TestStatus.PASSED
    
    @property
    def failed_count(self) -> int:
        if not self.step_results:
            return 0
        return sum(1 for s in self.step_results if not s.success)


@dataclass
class ExecutionSummary:
    """执行摘要"""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    total_steps: int = 0
    total_duration: float = 0.0
    success_rate: float = 0.0
    start_time: datetime = None
    end_time: datetime = None
    results: List[TestCaseResult] = None


class TestExecutor:
    """测试执行引擎"""
    
    def __init__(
        self,
        config: Optional[TestConfig] = None,
        client: Optional[HttpClient] = None
    ):
        self.config = config or TestConfig()
        self.client = client or HttpClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            headers=self.config.headers,
            cookies=self.config.cookies,
            verify_ssl=self.config.verify_ssl,
            redirect=self.config.redirect,
            max_retries=self.config.retries,
            retry_delay=self.config.retry_delay
        )
        
        self.assertion_engine = AssertionEngine()
        self.variable_manager = VariableManager()
        
        self.variable_manager.update(self.config.variables)
        
        self.results: List[TestCaseResult] = []
        self.execution_summary: ExecutionSummary = None
        
        self._setup_hooks: List[Callable] = []
        self._teardown_hooks: List[Callable] = []
        self._lock = threading.Lock()
        
        logger.info("测试执行引擎初始化完成")
    
    def add_setup_hook(self, hook: Callable):
        """添加前置钩子"""
        self._setup_hooks.append(hook)
    
    def add_teardown_hook(self, hook: Callable):
        """添加后置钩子"""
        self._teardown_hooks.append(hook)
    
    def execute_test_suite(
        self,
        suite: TestSuite,
        concurrent: bool = False
    ) -> ExecutionSummary:
        """执行测试套件"""
        self.results = []
        self.execution_summary = ExecutionSummary(
            start_time=datetime.now(),
            results=[]
        )
        
        logger.info(f"开始执行测试套件: {suite.name} ({len(suite.test_cases)} 个测试用例)")
        
        if concurrent:
            self._execute_concurrent(suite.test_cases)
        else:
            self._execute_sequential(suite.test_cases)
        
        self._finalize_summary()
        
        logger.info(f"测试套件执行完成 - 通过: {self.execution_summary.passed_tests}, "
                   f"失败: {self.execution_summary.failed_tests}")
        
        return self.execution_summary
    
    def execute_test_case(self, test_case: TestCase) -> TestCaseResult:
        """执行单个测试用例"""
        start_time = datetime.now()
        
        logger.info(f"开始执行测试用例: {test_case.name}")
        
        result = TestCaseResult(
            test_case_name=test_case.name,
            status=TestStatus.RUNNING,
            step_results=[],
            start_time=start_time
        )
        
        try:
            for hook in self._setup_hooks:
                hook(test_case, self.variable_manager)
            
            for hook in test_case.setup_hooks:
                hook(test_case, self.variable_manager)
            
            local_vars = VariableManager()
            local_vars.update(test_case.variables)
            
            for step in test_case.steps:
                if step.skip:
                    step_result = StepResult(
                        step_name=step.name,
                        status=TestStatus.SKIPPED
                    )
                    result.step_results.append(step_result)
                    continue
                
                step_result = self._execute_step(step, local_vars)
                result.step_results.append(step_result)
                
                if not step_result.success and self.config.fail_fast:
                    break
            
            all_passed = all(s.success for s in result.step_results if s.status != TestStatus.SKIPPED)
            result.status = TestStatus.PASSED if all_passed else TestStatus.FAILED
            
            for hook in test_case.teardown_hooks:
                hook(test_case, self.variable_manager, result)
            
            for hook in self._teardown_hooks:
                hook(test_case, self.variable_manager, result)
                
        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_message = str(e)
            logger.error(f"测试用例执行错误: {test_case.name} - {e}\n{traceback.format_exc()}")
        
        finally:
            end_time = datetime.now()
            result.end_time = end_time
            result.total_duration = (end_time - start_time).total_seconds()
            
            test_case.status = result.status
            test_case.results = result.step_results
        
        with self._lock:
            self.results.append(result)
        
        logger.info(f"测试用例执行完成: {test_case.name} - 状态: {result.status.value} "
                   f"(耗时: {result.total_duration:.2f}s)")
        
        return result
    
    def _execute_step(self, step: TestStep, variable_manager: VariableManager) -> StepResult:
        """执行单个步骤"""
        start_time = datetime.now()
        
        logger.debug(f"执行步骤: {step.name} ({step.method} {step.url})")
        
        step_result = StepResult(
            step_name=step.name,
            status=TestStatus.RUNNING,
            assertion_results=[],
            extracted_variables={},
            start_time=start_time
        )
        
        try:
            url = variable_manager.substitute_variables(step.url)
            params = variable_manager.substitute_in_dict(step.params) if step.params else None
            headers = variable_manager.substitute_in_dict(step.headers) if step.headers else None
            body = variable_manager.substitute_in_dict(step.body) if step.body else None
            json_body = variable_manager.substitute_in_dict(step.json_body) if step.json_body else None
            
            kwargs = {
                'timeout': step.timeout or self.config.timeout
            }
            
            if params:
                kwargs['params'] = params
            if headers:
                kwargs['headers'] = headers
            if body:
                kwargs['data'] = body
            if json_body:
                kwargs['json'] = json_body
            
            method_lower = step.method.lower()
            request_method = getattr(self.client, method_lower, None)
            
            if not request_method:
                raise ValueError(f"不支持的 HTTP 方法: {step.method}")
            
            request_result = request_method(url, **kwargs)
            step_result.request_result = request_result
            
            if not request_result.success:
                step_result.status = TestStatus.ERROR
                step_result.error_message = request_result.error
                return step_result
            
            response = request_result.response
            
            if step.validate_status_code:
                status_assertion = self.assertion_engine.assert_status_code(
                    response.status_code,
                    step.expected_status_code
                )
                step_result.assertion_results.append(status_assertion)
                
                if not status_assertion.success:
                    step_result.status = TestStatus.FAILED
            
            if step.assertions:
                response_data = {
                    'body': response.body,
                    'headers': response.headers,
                    'status_code': response.status_code
                }
                
                assertions_passed = True
                for assertion in step.assertions:
                    actual_value = response.body
                    
                    if assertion.actual_path:
                        actual_value = self.assertion_engine.extract_value(
                            response_data,
                            assertion.actual_path
                        )
                    
                    assert_result = self.assertion_engine.execute_assertion(
                        assertion_type=assertion.type,
                        actual=actual_value,
                        expected=assertion.expected,
                        message=assertion.message
                    )
                    
                    step_result.assertion_results.append(assert_result)
                    
                    if not assert_result.success:
                        assertions_passed = False
                
                if not assertions_passed and step_result.status != TestStatus.FAILED:
                    step_result.status = TestStatus.FAILED
            
            if step.extracts:
                response_data = {
                    'body': response.body,
                    'headers': response.headers,
                    'status_code': response.status_code
                }
                
                for extract_rule in step.extracts:
                    value = variable_manager.extract_from_response(
                        response_data,
                        extract_rule.expression,
                        extract_rule.from_response
                    )
                    
                    if value is not None:
                        variable_manager.set(extract_rule.name, value)
                        step_result.extracted_variables[extract_rule.name] = value
                        
                        self.variable_manager.set(extract_rule.name, value)
                        
                        logger.debug(f"提取变量: {extract_rule.name} = {value}")
            
            if step_result.status == TestStatus.RUNNING:
                step_result.status = TestStatus.PASSED
                
        except Exception as e:
            step_result.status = TestStatus.ERROR
            step_result.error_message = str(e)
            logger.error(f"步骤执行错误: {step.name} - {e}\n{traceback.format_exc()}")
        
        finally:
            end_time = datetime.now()
            step_result.end_time = end_time
            step_result.duration = (end_time - start_time).total_seconds()
            
            step.status = step_result.status
            step.result = step_result
        
        return step_result
    
    def _execute_sequential(self, test_cases: List[TestCase]):
        """顺序执行测试用例"""
        for test_case in test_cases:
            if test_case.skip:
                result = TestCaseResult(
                    test_case_name=test_case.name,
                    status=TestStatus.SKIPPED
                )
                self.results.append(result)
                continue
            
            self.execute_test_case(test_case)
    
    def _execute_concurrent(self, test_cases: List[TestCase]):
        """并发执行测试用例"""
        active_test_cases = [tc for tc in test_cases if not tc.skip]
        
        with ThreadPoolExecutor(max_workers=self.config.concurrent) as executor:
            futures = {
                executor.submit(self.execute_test_case, tc): tc 
                for tc in active_test_cases
            }
            
            for future in as_completed(futures):
                test_case = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"并发执行错误: {test_case.name} - {e}")
    
    def _finalize_summary(self):
        """生成执行摘要"""
        end_time = datetime.now()
        
        summary = ExecutionSummary(
            total_tests=len(self.results),
            passed_tests=sum(1 for r in self.results if r.passed),
            failed_tests=sum(1 for r in self.results if r.status == TestStatus.FAILED),
            skipped_tests=sum(1 for r in self.results if r.status == TestStatus.SKIPPED),
            error_tests=sum(1 for r in self.results if r.status == TestStatus.ERROR),
            total_steps=sum(len(r.step_results) for r in self.results),
            total_duration=(end_time - self.execution_summary.start_time).total_seconds(),
            start_time=self.execution_summary.start_time,
            end_time=end_time,
            results=self.results
        )
        
        if summary.total_tests > 0:
            summary.success_rate = (summary.passed_tests / summary.total_tests) * 100
        
        self.execution_summary = summary
    
    def get_failed_results(self) -> List[TestCaseResult]:
        """获取失败的测试结果"""
        return [r for r in self.results if not r.passed]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.execution_summary:
            return {}
        
        return {
            'total': self.execution_summary.total_tests,
            'passed': self.execution_summary.passed_tests,
            'failed': self.execution_summary.failed_tests,
            'skipped': self.execution_summary.skipped_tests,
            'error': self.execution_summary.error_tests,
            'success_rate': f"{self.execution_summary.success_rate:.2f}%",
            'duration': f"{self.execution_summary.total_duration:.2f}s",
            'total_steps': self.execution_summary.total_steps
        }
    
    def close(self):
        """关闭执行器"""
        self.client.close()
        logger.info("测试执行引擎已关闭")


# 需要添加 dataclass 导入
from dataclasses import dataclass