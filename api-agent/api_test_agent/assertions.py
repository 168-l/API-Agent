import re
import json
import operator
from typing import Any, Dict, List, Optional, Tuple
from functools import reduce
import jsonschema
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AssertionError(Exception):
    """断言错误"""
    pass


class AssertionResult:
    """断言结果"""
    
    def __init__(self, success: bool, message: str = "", expected: Any = None, actual: Any = None):
        self.success = success
        self.message = message
        self.expected = expected
        self.actual = actual
        self.timestamp = datetime.now()
    
    def __bool__(self):
        return self.success
    
    def __repr__(self):
        status = "✓" if self.success else "✗"
        return f"[{status}] {self.message}"


class AssertionEngine:
    """断言引擎"""
    
    OPERATORS = {
        'eq': operator.eq,
        'ne': operator.ne,
        'gt': operator.gt,
        'lt': operator.lt,
        'gte': operator.ge,
        'lte': operator.le,
        'in': lambda a, b: a in b,
        'not_in': lambda a, b: a not in b,
        'contains': lambda a, b: b in a,
        'not_contains': lambda a, b: b not in a,
        'startswith': lambda a, b: str(a).startswith(str(b)),
        'endswith': lambda a, b: str(a).endswith(str(b)),
        'is_empty': lambda a: len(a) == 0 if hasattr(a, '__len__') else a is None,
        'not_empty': lambda a: len(a) > 0 if hasattr(a, '__len__') else a is not None,
        'is_none': lambda a: a is None,
        'not_none': lambda a: a is not None,
        'type_is': lambda a, b: isinstance(a, b),
        'length_eq': lambda a, b: len(a) == b,
        'length_gt': lambda a, b: len(a) > b,
        'length_lt': lambda a, b: len(a) < b,
    }
    
    def __init__(self):
        self.custom_assertions = {}
    
    def register_assertion(self, name: str, func: callable):
        """注册自定义断言"""
        self.custom_assertions[name] = func
        logger.info(f"注册自定义断言: {name}")
    
    def assert_equals(self, actual: Any, expected: Any, message: str = "") -> AssertionResult:
        """相等断言"""
        success = actual == expected
        msg = message or f"期望值等于 {expected}, 实际值 {actual}"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected=expected,
            actual=actual
        )
    
    def assert_not_equals(self, actual: Any, expected: Any, message: str = "") -> AssertionResult:
        """不等断言"""
        success = actual != expected
        msg = message or f"期望值不等于 {expected}, 实际值 {actual}"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected=f"!= {expected}",
            actual=actual
        )
    
    def assert_greater_than(self, actual: Any, expected: Any, message: str = "") -> AssertionResult:
        """大于断言"""
        success = actual > expected
        msg = message or f"期望值大于 {expected}, 实际值 {actual}"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected=f"> {expected}",
            actual=actual
        )
    
    def assert_less_than(self, actual: Any, expected: Any, message: str = "") -> AssertionResult:
        """小于断言"""
        success = actual < expected
        msg = message or f"期望值小于 {expected}, 实际值 {actual}"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected=f"< {expected}",
            actual=actual
        )
    
    def assert_in(self, item: Any, container: Any, message: str = "") -> AssertionResult:
        """包含断言"""
        success = item in container
        msg = message or f"期望 {item} 在 {container} 中"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected=f"in {container}",
            actual=item
        )
    
    def assert_not_in(self, item: Any, container: Any, message: str = "") -> AssertionResult:
        """不包含断言"""
        success = item not in container
        msg = message or f"期望 {item} 不在 {container} 中"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected=f"not in {container}",
            actual=item
        )
    
    def assert_contains(self, text: str, substring: str, message: str = "") -> AssertionResult:
        """字符串包含断言"""
        success = substring in str(text)
        msg = message or f"期望字符串包含 '{substring}'"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected=f"contains '{substring}'",
            actual=text
        )
    
    def assert_regex(self, text: str, pattern: str, message: str = "") -> AssertionResult:
        """正则匹配断言"""
        match = re.search(pattern, str(text))
        success = match is not None
        msg = message or f"期望匹配正则 '{pattern}'"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected=f"regex: {pattern}",
            actual=text
        )
    
    def assert_schema(self, data: Any, schema: Dict[str, Any], message: str = "") -> AssertionResult:
        """JSON Schema 验证"""
        try:
            jsonschema.validate(data, schema)
            success = True
            error_msg = ""
        except jsonschema.ValidationError as e:
            success = False
            error_msg = str(e)
        
        msg = message or f"JSON Schema 验证 {'通过' if success else '失败'}"
        if error_msg:
            msg += f": {error_msg}"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected="valid schema",
            actual=data
        )
    
    def assert_status_code(self, actual: int, expected: int, message: str = "") -> AssertionResult:
        """状态码断言"""
        success = actual == expected
        msg = message or f"期望状态码 {expected}, 实际 {actual}"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected=expected,
            actual=actual
        )
    
    def assert_response_time(self, actual: float, max_time: float, message: str = "") -> AssertionResult:
        """响应时间断言"""
        success = actual <= max_time
        msg = message or f"响应时间 {actual}s 应小于 {max_time}s"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected=f"<={max_time}s",
            actual=f"{actual}s"
        )
    
    def assert_type(self, value: Any, expected_type: type, message: str = "") -> AssertionResult:
        """类型断言"""
        success = isinstance(value, expected_type)
        type_name = expected_type.__name__
        msg = message or f"期望类型为 {type_name}"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected=type_name,
            actual=type(value).__name__
        )
    
    def assert_length(self, obj: Any, expected_length: int, message: str = "") -> AssertionResult:
        """长度断言"""
        actual_length = len(obj) if hasattr(obj, '__len__') else 0
        success = actual_length == expected_length
        msg = message or f"期望长度为 {expected_length}, 实际 {actual_length}"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected=expected_length,
            actual=actual_length
        )
    
    def assert_true(self, value: Any, message: str = "") -> AssertionResult:
        """真值断言"""
        success = bool(value)
        msg = message or f"期望值为真"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected=True,
            actual=value
        )
    
    def assert_false(self, value: Any, message: str = "") -> AssertionResult:
        """假值断言"""
        success = not bool(value)
        msg = message or f"期望值为假"
        
        return AssertionResult(
            success=success,
            message=msg,
            expected=False,
            actual=value
        )
    
    def execute_assertion(
        self,
        assertion_type: str,
        actual: Any,
        expected: Any = None,
        message: str = "",
        **kwargs
    ) -> AssertionResult:
        """执行断言"""
        if assertion_type in self.custom_assertions:
            return self.custom_assertions[assertion_type](actual, expected, **kwargs)
        
        assertions_map = {
            'eq': lambda: self.assert_equals(actual, expected, message),
            'ne': lambda: self.assert_not_equals(actual, expected, message),
            'gt': lambda: self.assert_greater_than(actual, expected, message),
            'lt': lambda: self.assert_less_than(actual, expected, message),
            'gte': lambda: self.assert_greater_than(actual, expected - 1, message),
            'lte': lambda: self.assert_less_than(actual, expected + 1, message),
            'in': lambda: self.assert_in(actual, expected, message),
            'not_in': lambda: self.assert_not_in(actual, expected, message),
            'contains': lambda: self.assert_contains(actual, expected, message),
            'not_contains': lambda: lambda: self.assert_not_in(expected, actual, message),
            'regex': lambda: self.assert_regex(actual, expected, message),
            'schema': lambda: self.assert_schema(actual, expected, message),
            'type': lambda: self.assert_type(actual, expected, message),
            'length': lambda: self.assert_length(actual, expected, message),
            'true': lambda: self.assert_true(actual, message),
            'false': lambda: self.assert_false(actual, message),
            'status_code': lambda: self.assert_status_code(actual, expected, message),
            'response_time': lambda: self.assert_response_time(actual, expected, message),
        }
        
        if assertion_type in assertions_map:
            return assertions_map[assertion_type]()
        else:
            raise ValueError(f"未知的断言类型: {assertion_type}")
    
    def validate_response(
        self,
        response,
        assertions: List[Dict[str, Any]],
        variable_extractor=None
    ) -> Tuple[List[AssertionResult], bool]:
        """验证响应"""
        results = []
        all_passed = True
        
        for assertion in assertions:
            assertion_type = assertion.get('type', 'eq')
            expected = assertion.get('expected')
            actual_path = assertion.get('actual_path')
            message = assertion.get('message', '')
            
            try:
                if actual_path:
                    actual = self.extract_value(response, actual_path)
                else:
                    actual = response
                
                result = self.execute_assertion(
                    assertion_type=assertion_type,
                    actual=actual,
                    expected=expected,
                    message=message
                )
                
                results.append(result)
                
                if not result.success:
                    all_passed = False
                    
            except Exception as e:
                results.append(AssertionResult(
                    success=False,
                    message=f"断言执行错误: {str(e)}"
                ))
                all_passed = False
        
        return results, all_passed
    
    def extract_value(self, obj: Any, path: str) -> Any:
        """从对象中提取值（支持 JSON Path）"""
        if not path:
            return obj
        
        parts = path.split('.')
        current = obj
        
        for part in parts:
            if current is None:
                raise ValueError(f"路径 '{path}' 在中间遇到空值")
            
            if '[' in part and ']' in part:
                key = part.split('[')[0]
                index = int(part.split('[')[1].split(']')[0])
                
                if key:
                    current = current[key]
                current = current[index]
            else:
                if isinstance(current, dict):
                    current = current.get(part)
                elif hasattr(current, part):
                    current = getattr(current, part)
                else:
                    raise ValueError(f"无法访问属性: {part}")
        
        return current