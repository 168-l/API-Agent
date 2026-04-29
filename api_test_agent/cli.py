"""API Test Agent - 主入口模块"""

import argparse
import sys
import os
import logging
from datetime import datetime

from .config import TestConfig, load_config
from .client import HttpClient
from .test_case import TestCase, TestSuite, TestStep, Assertion, ExtractRule
from .executor import TestExecutor
from .assertions import AssertionEngine
from .variables import VariableManager
from .report_generator import ReportGenerator


def setup_logging(level: str = "INFO"):
    """配置日志"""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


class APITestAgent:
    """API 测试 Agent 主类"""
    
    def __init__(self, config_path: str = None):
        self.config = load_config(config_path)
        self.executor = None
        self.report_generator = ReportGenerator(self.config.output_dir)
        
        setup_logging(self.config.log_level)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("🚀 API Test Agent 初始化完成")
    
    def run_tests(
        self,
        test_files: list = None,
        test_dir: str = None,
        tags: list = None,
        concurrent: bool = False
    ):
        """运行测试"""
        self.logger.info("="*60)
        self.logger.info("开始执行 API 测试")
        self.logger.info("="*60)
        
        try:
            with TestExecutor(self.config) as executor:
                self.executor = executor
                
                if test_dir:
                    suite = TestSuite.from_directory(test_dir)
                elif test_files:
                    suite = TestSuite(name="Custom Suite")
                    for file in test_files:
                        if file.endswith('.json'):
                            tc = TestCase.from_json(file)
                        else:
                            tc = TestCase.from_yaml(file)
                        suite.add_test_case(tc)
                else:
                    raise ValueError("必须指定测试文件或目录")
                
                if tags:
                    suite = suite.filter_by_tags(tags)
                
                summary = executor.execute_test_suite(suite, concurrent=concurrent)
                
                self.report_generator.generate_console_summary(summary)
                self.report_generator.generate_html_report(summary)
                self.report_generator.generate_json_report(summary)
                
                return summary.failed_tests == 0
                
        except Exception as e:
            self.logger.error(f"测试执行失败: {e}")
            raise
    
    def run_single_test(self, test_file: str):
        """运行单个测试用例"""
        if test_file.endswith('.json'):
            test_case = TestCase.from_json(test_file)
        else:
            test_case = TestCase.from_yaml(test_file)
        
        suite = TestSuite(name="Single Test")
        suite.add_test_case(test_case)
        
        return self.run_tests(test_suite=suite)


def main():
    """CLI 主函数"""
    parser = argparse.ArgumentParser(
        description='🧪 API 接口自动化测试 Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s run -d tests/                    # 运行 tests/ 目录下的所有测试
  %(prog)s run -f test_api.yaml             # 运行单个测试文件
  %(prog)s run -f test1.yaml test2.yaml     # 运行多个测试文件
  %(prog)s run -d tests/ --tags smoke       # 运行带 smoke 标签的测试
  %(prog)s run -d tests/ --concurrent       # 并发执行测试
  %(prog)s run -c config.yaml -d tests/     # 使用配置文件运行测试
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # run 命令
    run_parser = subparsers.add_parser('run', help='运行测试')
    run_parser.add_argument(
        '-f', '--files',
        nargs='+',
        help='测试文件路径 (支持 .yaml, .yml, .json)'
    )
    run_parser.add_argument(
        '-d', '--dir',
        help='测试目录'
    )
    run_parser.add_argument(
        '-c', '--config',
        help='配置文件路径'
    )
    run_parser.add_argument(
        '--tags',
        nargs='+',
        help='按标签过滤测试'
    )
    run_parser.add_argument(
        '--concurrent',
        action='store_true',
        help='并发执行测试'
    )
    run_parser.add_argument(
        '--output',
        default='./reports',
        help='报告输出目录 (默认: ./reports)'
    )
    run_parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='日志级别 (默认: INFO)'
    )
    
    # init 命令
    init_parser = subparsers.add_parser('init', help='初始化项目结构')
    init_parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='项目路径 (默认: 当前目录)'
    )
    
    # generate 命令
    gen_parser = subparsers.add_parser('generate', help='生成测试用例模板')
    gen_parser.add_argument(
        '-o', '--output',
        default='example_test.yaml',
        help='输出文件名 (默认: example_test.yaml)'
    )
    gen_parser.add_argument(
        '-t', '--type',
        choices=['basic', 'advanced', 'crud'],
        default='basic',
        help='模板类型 (默认: basic)'
    )
    
    args = parser.parse_args()
    
    if args.command == 'run':
        _run_command(args)
    elif args.command == 'init':
        _init_command(args)
    elif args.command == 'generate':
        _generate_command(args)
    else:
        parser.print_help()


def _run_command(args):
    """执行 run 命令"""
    setup_logging(args.log_level)
    
    agent = APITestAgent(config_path=args.config)
    agent.config.output_dir = args.output
    
    success = agent.run_tests(
        test_files=args.files,
        test_dir=args.dir,
        tags=args.tags,
        concurrent=args.concurrent
    )
    
    sys.exit(0 if success else 1)


def _init_command(args):
    """执行 init 命令"""
    base_path = os.path.abspath(args.path)
    
    dirs_to_create = [
        base_path,
        os.path.join(base_path, 'tests'),
        os.path.join(base_path, 'config'),
        os.path.join(base_path, 'reports'),
    ]
    
    for dir_path in dirs_to_create:
        os.makedirs(dir_path, exist_ok=True)
        print(f"✓ 创建目录: {dir_path}")
    
    config_content = """# API 测试配置文件
base_url: "http://localhost:8000/api"
timeout: 30
retries: 3
retry_delay: 1.0

headers:
  Content-Type: application/json
  Accept: application/json

variables:
  username: "testuser"
  password: "testpass123"

environment: test

output_dir: "./reports"
log_level: INFO

concurrent: 5
fail_fast: false

verify_ssl: true
redirect: true
"""
    
    config_path = os.path.join(base_path, 'config', 'default_config.yaml')
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)
    print(f"✓ 创建配置文件: {config_path}")
    
    example_test = """# 示例测试用例
name: 用户 API 测试
description: 测试用户相关的 API 接口
tags:
  - user
  - api
  - smoke

variables:
  user_id: 1

steps:
  # 获取用户列表
  - name: 获取用户列表
    method: GET
    url: /users
    expected_status_code: 200
    assertions:
      - type: status_code
        expected: 200
      - type: eq
        actual_path: code
        expected: 0
      - type: contains
        actual_path: message
        expected: success
    extracts:
      - name: first_user_id
        expression: data.0.id
        from_response: body
  
  # 获取单个用户详情
  - name: 获取用户详情
    method: GET
    url: /users/${first_user_id}
    expected_status_code: 200
    assertions:
      - type: status_code
        expected: 200
      - type: eq
        actual_path: data.id
        expected: "${first_user_id}"
  
  # 创建新用户
  - name: 创建用户
    method: POST
    url: /users
    json:
      username: "new_user_{{timestamp}}"
      email: "test@example.com"
      password: "password123"
    expected_status_code: 201
    assertions:
      - type: status_code
        expected: 201
      - type: eq
        actual_path: code
        expected: 0
    extracts:
      - name: new_user_id
        expression: data.id
        from_response: body
  
  # 更新用户信息
  - name: 更新用户
    method: PUT
    url: /users/${new_user_id}
    json:
      username: "updated_user"
    expected_status_code: 200
    assertions:
      - type: status_code
        expected: 200
  
  # 删除用户
  - name: 删除用户
    method: DELETE
    url: /users/${new_user_id}
    expected_status_code: 204
    assertions:
      - type: status_code
        expected: 204
"""
    
    test_path = os.path.join(base_path, 'tests', 'example_test.yaml')
    with open(test_path, 'w', encoding='utf-8') as f:
        f.write(example_test)
    print(f"✓ 创建示例测试: {test_path}")
    
    readme_content = """# API 自动化测试项目

## 项目结构

```
├── config/
│   └── default_config.yaml   # 配置文件
├── tests/
│   └── example_test.yaml     # 示例测试用例
├── reports/                   # 测试报告输出目录
└── README.md                  # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 修改配置

编辑 `config/default_config.yaml`，设置你的 API 地址和认证信息。

### 3. 编写测试用例

在 `tests/` 目录下创建 `.yaml` 或 `.json` 格式的测试文件。

### 4. 运行测试

```bash
# 运行所有测试
python -m api_test_agent run -d tests/

# 运行单个测试文件
python -m api_test_agent run -f tests/example_test.yaml

# 使用配置文件运行
python -m api_test_agent run -c config/default_config.yaml -d tests/

# 并发执行
python -m api_test_agent run -d tests/ --concurrent

# 按标签过滤
python -m api_test_agent run -d tests/ --tags smoke
```

## 测试报告

测试完成后，报告将保存在 `reports/` 目录下：
- HTML 报告：可视化查看测试结果
- JSON 报告：机器可读格式，便于集成

## 特性

- ✅ 支持 RESTful API 测试（GET/POST/PUT/DELETE 等）
- ✅ YAML/JSON 格式测试用例
- ✅ 变量提取和引用
- ✅ 丰富的断言类型
- ✅ 数据驱动测试
- ✅ 并发执行
- ✅ 自动重试机制
- ✅ 详细的 HTML 报告
- ✅ 钩子函数支持
"""
    
    readme_path = os.path.join(base_path, 'README.md')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"✓ 创建说明文档: {readme_path}")
    
    print(f"\n✨ 项目初始化完成！")
    print(f"📍 路径: {base_path}")
    print(f"\n下一步:")
    print(f"  1. 编辑 config/default_config.yaml 配置 API 地址")
    print(f"  2. 在 tests/ 目录编写测试用例")
    print(f"  3. 运行: python -m api_test_agent run -d tests/")


def _generate_command(args):
    """执行 generate 命令"""
    templates = {
        'basic': """# 基本 API 测试模板
name: 基本 API 测试
description: 这是一个基本的 API 测试示例

steps:
  - name: GET 请求示例
    method: GET
    url: /api/endpoint
    expected_status_code: 200
    assertions:
      - type: status_code
        expected: 200
""",
        'advanced': """# 高级 API 测试模板
name: 高级 API 测试
description: 包含变量、提取、断言的高级示例

variables:
  token: ""

steps:
  # 1. 登录获取 Token
  - name: 用户登录
    method: POST
    url: /auth/login
    json:
      username: "admin"
      password: "admin123"
    expected_status_code: 200
    assertions:
      - type: status_code
        expected: 200
      - type: eq
        actual_path: code
        expected: 0
    extracts:
      - name: token
        expression: data.token
        from_response: body
  
  # 2. 使用 Token 访问受保护接口
  - name: 获取用户信息
    method: GET
    url: /user/profile
    headers:
      Authorization: "Bearer ${token}"
    expected_status_code: 200
    assertions:
      - type: status_code
        expected: 200
      - type: eq
        actual_path: data.username
        expected: "admin"
""",
        'crud': """# CRUD 操作测试模板
name: CRUD 完整测试
description: Create, Read, Update, Delete 完整流程测试

variables:
  resource_id: null

steps:
  # Create - 创建资源
  - name: 创建资源
    method: POST
    url: /resources
    json:
      name: "Test Resource"
      description: "Created by automated test"
    expected_status_code: 201
    assertions:
      - type: status_code
        expected: 201
      - type: eq
        actual_path: code
        expected: 0
    extracts:
      - name: resource_id
        expression: data.id
        from_response: body
  
  # Read - 读取资源
  - name: 读取资源详情
    method: GET
    url: /resources/${resource_id}
    expected_status_code: 200
    assertions:
      - type: status_code
        expected: 200
      - type: eq
        actual_path: data.id
        expected: "${resource_id}"
  
  # Update - 更新资源
  - name: 更新资源
    method: PUT
    url: /resources/${resource_id}
    json:
      name: "Updated Resource"
      description: "Updated by test"
    expected_status_code: 200
    assertions:
      - type: status_code
        expected: 200
      - type: eq
        actual_path: data.name
        expected: "Updated Resource"
  
  # List - 列表查询
  - name: 查询资源列表
    method: GET
    url: /resources
    params:
      page: 1
      size: 10
    expected_status_code: 200
    assertions:
      - type: status_code
        expected: 200
      - type: length_gt
        actual_path: data
        expected: 0
  
  # Delete - 删除资源
  - name: 删除资源
    method: DELETE
    url: /resources/${resource_id}
    expected_status_code: 204
    assertions:
      - type: status_code
        expected: 204
  
  # Verify - 验证删除
  - name: 验证删除结果
    method: GET
    url: /resources/${resource_id}
    expected_status_code: 404
    assertions:
      - type: status_code
        expected: 404
"""
    }
    
    template = templates.get(args.type, templates['basic'])
    
    output_path = os.path.abspath(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(template)
    
    print(f"✓ 已生成测试模板: {output_path}")


if __name__ == '__main__':
    main()