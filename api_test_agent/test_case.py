import os
import yaml
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import copy
import logging

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class Assertion:
    """断言定义"""
    type: str  # eq, ne, gt, lt, gte, lte, in, not_in, contains, regex, schema, etc.
    expected: Any
    actual_path: Optional[str] = None  # JSON path to extract actual value
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type,
            'expected': self.expected,
            'actual_path': self.actual_path,
            'message': self.message
        }


@dataclass
class ExtractRule:
    """提取规则"""
    name: str
    expression: str  # JSON path or regex
    from_response: str = "body"  # body, headers, status_code
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'expression': self.expression,
            'from_response': self.from_response
        }


@dataclass
class TestStep:
    """测试步骤"""
    name: str
    method: str  # GET, POST, PUT, DELETE, etc.
    url: str
    
    params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    cookies: Optional[Dict[str, str]] = None
    body: Any = None
    json_body: Any = None
    
    assertions: List[Assertion] = field(default_factory=list)
    extracts: List[ExtractRule] = field(default_factory=list)
    
    setup_hooks: List[str] = field(default_factory=list)
    teardown_hooks: List[str] = field(default_factory=list)
    
    skip: bool = False
    timeout: Optional[int] = None
    
    validate_status_code: bool = True
    expected_status_code: int = 200
    
    result: Optional[Any] = None
    status: TestStatus = TestStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        data = {
            'name': self.name,
            'method': self.method,
            'url': self.url,
        }
        
        if self.params:
            data['params'] = self.params
        if self.headers:
            data['headers'] = self.headers
        if self.body is not None:
            data['body'] = self.body
        if self.json_body is not None:
            data['json'] = self.json_body
        if self.assertions:
            data['assertions'] = [a.to_dict() for a in self.assertions]
        if self.extracts:
            data['extracts'] = [e.to_dict() for e in self.extracts]
        if self.skip:
            data['skip'] = self.skip
        if self.timeout:
            data['timeout'] = self.timeout
        
        return data


@dataclass
class TestCase:
    """测试用例"""
    name: str
    description: str = ""
    
    steps: List[TestStep] = field(default_factory=list)
    
    variables: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    setup_hooks: List[Callable] = field(default_factory=list)
    teardown_hooks: List[Callable] = field(default_factory=list)
    
    skip: bool = False
    priority: int = 0  # 0-10, higher = more important
    
    config: Optional[Dict[str, Any]] = None
    
    status: TestStatus = TestStatus.PENDING
    results: List[Any] = field(default_factory=list)
    
    file_path: Optional[str] = None
    
    @classmethod
    def from_yaml(cls, file_path: str) -> 'TestCase':
        """从 YAML 文件加载测试用例"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        test_case = cls._from_dict(data)
        test_case.file_path = file_path
        
        logger.info(f"加载测试用例: {file_path}")
        return test_case
    
    @classmethod
    def from_json(cls, file_path: str) -> 'TestCase':
        """从 JSON 文件加载测试用例"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        test_case = cls._from_dict(data)
        test_case.file_path = file_path
        
        logger.info(f"加载测试用例: {file_path}")
        return test_case
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """从字典创建测试用例"""
        steps = []
        for step_data in data.get('steps', []):
            step = TestStep(
                name=step_data.get('name', ''),
                method=step_data.get('method', 'GET'),
                url=step_data.get('url', ''),
                params=step_data.get('params'),
                headers=step_data.get('headers'),
                body=step_data.get('body'),
                json_body=step_data.get('json'),
                skip=step_data.get('skip', False),
                timeout=step_data.get('timeout'),
                expected_status_code=step_data.get('expected_status_code', 200),
                validate_status_code=step_data.get('validate_status_code', True)
            )
            
            for assert_data in step_data.get('assertions', []):
                assertion = Assertion(
                    type=assert_data.get('type', 'eq'),
                    expected=assert_data.get('expected'),
                    actual_path=assert_data.get('actual_path'),
                    message=assert_data.get('message', '')
                )
                step.assertions.append(assertion)
            
            for extract_data in step_data.get('extracts', []):
                extract = ExtractRule(
                    name=extract_data.get('name'),
                    expression=extract_data.get('expression'),
                    from_response=extract_data.get('from_response', 'body')
                )
                step.extracts.append(extract)
            
            steps.append(step)
        
        return cls(
            name=data.get('name', 'Unnamed Test'),
            description=data.get('description', ''),
            steps=steps,
            variables=data.get('variables', {}),
            tags=data.get('tags', []),
            skip=data.get('skip', False),
            priority=data.get('priority', 0),
            config=data.get('config')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'description': self.description,
            'steps': [s.to_dict() for s in self.steps],
            'variables': self.variables,
            'tags': self.tags,
            'skip': self.skip,
            'priority': self.priority,
            'status': self.status.value
        }
    
    def add_step(self, step: TestStep):
        """添加测试步骤"""
        self.steps.append(step)


@dataclass
class TestSuite:
    """测试套件"""
    name: str
    description: str = ""
    
    test_cases: List[TestCase] = field(default_factory=list)
    
    variables: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    setup_hooks: List[Callable] = field(default_factory=list)
    teardown_hooks: List[Callable] = field(default_factory=list)
    
    skip: bool = False
    
    status: TestStatus = TestStatus.PENDING
    results: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_directory(cls, directory: str) -> 'TestSuite':
        """从目录加载所有测试用例"""
        suite = cls(name=os.path.basename(directory))
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(('.yaml', '.yml', '.json')):
                    file_path = os.path.join(root, file)
                    
                    try:
                        if file.endswith('.json'):
                            test_case = TestCase.from_json(file_path)
                        else:
                            test_case = TestCase.from_yaml(file_path)
                        
                        suite.test_cases.append(test_case)
                        
                    except Exception as e:
                        logger.error(f"加载失败 {file_path}: {e}")
        
        logger.info(f"从目录 {directory} 加载了 {len(suite.test_cases)} 个测试用例")
        return suite
    
    def add_test_case(self, test_case: TestCase):
        """添加测试用例"""
        self.test_cases.append(test_case)
    
    def filter_by_tags(self, tags: List[str]) -> 'TestSuite':
        """根据标签过滤"""
        filtered_suite = TestSuite(
            name=f"{self.name} (filtered)",
            description=self.description
        )
        
        for tc in self.test_cases:
            if any(tag in tc.tags for tag in tags):
                filtered_suite.add_test_case(tc)
        
        return filtered_suite
    
    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        stats = {
            'total': len(self.test_cases),
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'error': 0,
            'pending': 0
        }
        
        for tc in self.test_cases:
            stats[tc.status.value] += 1
        
        return stats


def load_test_cases_from_yaml(file_paths: List[str]) -> List[TestCase]:
    """批量加载 YAML 测试用例"""
    test_cases = []
    
    for path in file_paths:
        try:
            test_case = TestCase.from_yaml(path)
            test_cases.append(test_case)
        except Exception as e:
            logger.error(f"加载失败 {path}: {e}")
    
    return test_cases


def load_test_cases_from_directory(directory: str) -> List[TestCase]:
    """从目录加载所有测试用例"""
    suite = TestSuite.from_directory(directory)
    return suite.test_cases