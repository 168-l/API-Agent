"""
API Test Agent 使用示例
演示如何使用 API 测试 Agent 进行自动化测试
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_test_agent import (
    HttpClient,
    TestCase,
    TestStep,
    Assertion,
    ExtractRule,
    TestExecutor,
    TestSuite,
    VariableManager,
    ReportGenerator,
    TestConfig
)
from api_test_agent.test_case import TestStatus


def example_1_basic_usage():
    """示例 1: 基本用法 - 快速开始"""
    print("\n" + "="*60)
    print("示例 1: 基本用法")
    print("="*60)
    
    # 1. 创建配置
    config = TestConfig(
        base_url="https://jsonplaceholder.typicode.com",
        timeout=10,
        headers={"Content-Type": "application/json"}
    )
    
    # 2. 创建测试用例
    test_case = TestCase(
        name="获取用户信息测试",
        description="测试 JSONPlaceholder 的用户接口"
    )
    
    # 3. 添加测试步骤
    step = TestStep(
        name="获取用户列表",
        method="GET",
        url="/users",
        expected_status_code=200
    )
    
    step.assertions.append(Assertion(
        type="status_code",
        expected=200,
        message="状态码应为 200"
    ))
    
    step.assertions.append(Assertion(
        type="length_gt",
        actual_path="$",
        expected=0,
        message="返回列表不应为空"
    ))
    
    step.extracts.append(ExtractRule(
        name="first_user_id",
        expression="0.id",
        from_response="body"
    ))
    
    test_case.add_step(step)
    
    # 添加第二个步骤：获取单个用户详情
    step2 = TestStep(
        name="获取第一个用户详情",
        method="GET",
        url="/users/${first_user_id}",
        expected_status_code=200
    )
    
    step2.assertions.append(Assertion(
        type="eq",
        actual_path="id",
        expected="${first_user_id}",
        message="用户 ID 应一致"
    ))
    
    step2.assertions.append(Assertion(
        type="not_empty",
        actual_path="name",
        message="用户名不应为空"
    ))
    
    test_case.add_step(step2)
    
    # 4. 执行测试
    with TestExecutor(config) as executor:
        result = executor.execute_test_case(test_case)
        
        print(f"\n测试结果: {result.status.value}")
        print(f"总耗时: {result.total_duration:.2f}s")
        
        for step_result in result.step_results:
            print(f"\n  步骤: {step_result.step_name}")
            print(f"  状态: {step_result.status.value}")
            if step_result.assertion_results:
                for assertion in step_result.assertion_results:
                    print(f"  断言: {'✓' if assertion.success else '✗'} {assertion.message}")


def example_2_yaml_test_case():
    """示例 2: 从 YAML 文件加载测试用例"""
    print("\n" + "="*60)
    print("示例 2: 从 YAML 文件加载测试用例")
    print("="*60)
    
    yaml_file = "tests/examples/user_api_test.yaml"
    
    if not os.path.exists(yaml_file):
        print(f"⚠️ 文件不存在，跳过此示例: {yaml_file}")
        return
    
    config = TestConfig(base_url="http://localhost:8000/api")
    
    test_case = TestCase.from_yaml(yaml_file)
    
    print(f"✓ 加载测试用例: {test_case.name}")
    print(f"  描述: {test_case.description}")
    print(f"  标签: {test_case.tags}")
    print(f"  步骤数: {len(test_case.steps)}")


def example_3_test_suite_execution():
    """示例 3: 测试套件执行"""
    print("\n" + "="*60)
    print("示例 3: 测试套件执行")
    print("="*60)
    
    config = TestConfig(
        base_url="https://jsonplaceholder.typicode.com",
        timeout=15,
        concurrent=3
    )
    
    suite = TestSuite(name="JSONPlaceholder API 测试套件")
    
    # 用例 1: 用户 API
    user_test = TestCase(name="用户 API 测试", tags=["user"])
    
    user_test.add_step(TestStep(
        name="获取所有用户",
        method="GET",
        url="/users",
        assertions=[
            Assertion(type="status_code", expected=200),
            Assertion(type="length_gt", actual_path="$", expected=0),
        ],
        extracts=[
            ExtractRule(name="user_count", expression="length", from_response="body")
        ]
    ))
    
    user_test.add_step(TestStep(
        name="创建新用户",
        method="POST",
        url="/users",
        json_body={
            "name": "Test User",
            "email": "test@example.com"
        },
        assertions=[
            Assertion(type="status_code", expected=201),
            Assertion(type="eq", actual_path="name", expected="Test User"),
        ]
    ))
    
    suite.add_test_case(user_test)
    
    # 用例 2: 文章 API
    post_test = TestCase(name="文章 API 测试", tags=["post"])
    
    post_test.add_step(TestStep(
        name="获取文章列表",
        method="GET",
        url="/posts",
        params={"_limit": 5},
        assertions=[
            Assertion(type="status_code", expected=200),
            Assertion(type="length_eq", actual_path="$", expected=5),
        ]
    ))
    
    post_test.add_step(TestStep(
        name="获取单篇文章",
        method="GET",
        url="/posts/1",
        assertions=[
            Assertion(type="status_code", expected=200),
            Assertion(type="not_empty", actual_path="title"),
            Assertion(type="not_empty", actual_path="body"),
        ]
    ))
    
    suite.add_test_case(post_test)
    
    # 执行测试套件
    with TestExecutor(config) as executor:
        report_gen = ReportGenerator("./reports")
        
        summary = executor.execute_test_suite(suite, concurrent=True)
        
        # 输出报告
        report_gen.generate_console_summary(summary)
        report_gen.generate_html_report(summary)
        report_gen.generate_json_report(summary)


def example_4_custom_assertions():
    """示例 4: 自定义断言"""
    print("\n" + "="*60)
    print("示例 4: 自定义断言")
    print("="*60)
    
    from api_test_agent.assertions import AssertionEngine
    
    engine = AssertionEngine()
    
    def custom_json_array_length_check(actual, expected, **kwargs):
        """自定义断言：检查 JSON 数组长度在指定范围内"""
        if isinstance(actual, list):
            min_len, max_len = expected
            success = min_len <= len(actual) <= max_len
            msg = f"数组长度 {len(actual)} 在 [{min_len}, {max_len}] 范围内"
            from api_test_agent.assertions import AssertionResult
            return AssertionResult(success=success, message=msg)
        raise ValueError("期望值为列表类型")
    
    # 注册自定义断言
    engine.register_assertion("array_length_range", custom_json_array_length_check)
    
    # 使用自定义断言
    test_data = [1, 2, 3, 4, 5]
    result = engine.execute_assertion(
        assertion_type="array_length_range",
        actual=test_data,
        expected=(1, 10),
        message="检查数组长度范围"
    )
    
    print(f"自定义断言结果: {'✓' if result.success else '✗'} {result.message}")


def example_5_variable_management():
    """示例 5: 变量管理"""
    print("\n" + "="*60)
    print("示例 5: 变量管理")
    print("="*60)
    
    vm = VariableManager()
    
    # 设置变量
    vm.set("base_url", "https://api.example.com")
    vm.set("token", "abc123xyz")
    vm.set("user_id", 10086)
    
    # 变量替换
    text = "API 地址: ${base_url}, Token: ${token}"
    substituted = vm.substitute_variables(text)
    print(f"原始文本: {text}")
    print(f"替换后:   {substituted}")
    
    # 在字典中替换变量
    data = {
        "url": "/users/${user_id}/profile",
        "headers": {
            "Authorization": "Bearer ${token}"
        }
    }
    
    processed_data = vm.substitute_in_dict(data)
    print(f"\n处理后的数据:")
    import json
    print(json.dumps(processed_data, indent=2, ensure_ascii=False))


def example_6_http_client_directly():
    """示例 6: 直接使用 HTTP 客户端"""
    print("\n" + "="*60)
    print("示例 6: 直接使用 HTTP 客户端")
    print("="*60)
    
    client = HttpClient(
        base_url="https://jsonplaceholder.typicode.com",
        timeout=10
    )
    
    try:
        # GET 请求
        result = client.get("/posts/1")
        
        if result.success:
            print(f"\n✓ GET 请求成功")
            print(f"  状态码: {result.response.status_code}")
            print(f"  响应时间: {result.response.elapsed:.3f}s")
            
            body = result.response.json()
            print(f"  标题: {body.get('title', 'N/A')}")
        else:
            print(f"✗ 请求失败: {result.error}")
        
        # POST 请求
        post_data = {
            "title": "Test Post",
            "body": "This is a test post content",
            "userId": 1
        }
        
        result = client.post("/posts", json=post_data)
        
        if result.success:
            print(f"\n✓ POST 请求成功")
            print(f"  返回数据 ID: {result.response.json().get('id')}")
        
    finally:
        client.close()


def main():
    """运行所有示例"""
    print("\n" + "🧪"*30)
    print("🎯 API Test Agent 使用示例")
    print("🧪"*30)
    
    examples = [
        ("基本用法", example_1_basic_usage),
        ("YAML 加载", example_2_yaml_test_case),
        ("测试套件", example_3_test_suite_execution),
        ("自定义断言", example_4_custom_assertions),
        ("变量管理", example_5_variable_management),
        ("HTTP 客户端", example_6_http_client_directly),
    ]
    
    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\n⚠️ 示例 '{name}' 出错: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("✨ 所有示例执行完成!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()