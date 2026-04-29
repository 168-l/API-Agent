import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from jinja2 import Template
import logging

from .executor import ExecutionSummary, TestCaseResult, StepResult, TestStatus

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"报告生成器初始化 - 输出目录: {output_dir}")
    
    def generate_html_report(
        self,
        summary: ExecutionSummary,
        filename: str = None
    ) -> str:
        """生成 HTML 报告"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.html"
        
        filepath = os.path.join(self.output_dir, filename)
        
        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API 测试报告</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background-color: #fafafa;
        }
        
        .summary-card {
            background: white;
            padding: 25px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            transition: transform 0.3s ease;
        }
        
        .summary-card:hover {
            transform: translateY(-5px);
        }
        
        .summary-card h3 {
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        
        .summary-card .value {
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
        }
        
        .card-total { border-left: 4px solid #667eea; }
        .card-passed { border-left: 4px solid #28a745; }
        .card-failed { border-left: 4px solid #dc3545; }
        .card-skipped { border-left: 4px solid #ffc107; }
        .card-error { border-left: 4px solid #fd7e14; }
        .card-duration { border-left: 4px solid #17a2b8; }
        .card-rate { border-left: 4px solid #6f42c1; }
        
        .passed { color: #28a745 !important; }
        .failed { color: #dc3545 !important; }
        .skipped { color: #ffc107 !important; }
        .error { color: #fd7e14 !important; }
        
        .results {
            padding: 30px;
        }
        
        .results h2 {
            margin-bottom: 20px;
            color: #333;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }
        
        .test-case {
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-bottom: 15px;
            overflow: hidden;
        }
        
        .test-case-header {
            padding: 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: #fafafa;
            transition: background-color 0.3s ease;
        }
        
        .test-case-header:hover {
            background-color: #f0f0f0;
        }
        
        .test-case-name {
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .test-case-status {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .status-passed { background-color: #d4edda; color: #155724; }
        .status-failed { background-color: #f8d7da; color: #721c24; }
        .status-skipped { background-color: #fff3cd; color: #856404; }
        .status-error { background-color: #ffeeba; color: #856404; }
        
        .test-case-details {
            display: none;
            padding: 20px;
            border-top: 1px solid #eee;
            background-color: white;
        }
        
        .test-case.active .test-case-details {
            display: block;
        }
        
        .step {
            background: #f9f9f9;
            border: 1px solid #eee;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 10px;
        }
        
        .step-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .step-name {
            font-weight: 600;
            color: #555;
        }
        
        .step-info {
            font-size: 0.9em;
            color: #888;
        }
        
        .assertions {
            margin-top: 10px;
        }
        
        .assertion-item {
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 4px;
            font-size: 0.9em;
        }
        
        .assertion-passed {
            background-color: #d4edda;
            color: #155724;
        }
        
        .assertion-failed {
            background-color: #f8d7da;
            color: #721c24;
        }
        
        .request-info, .response-info {
            background: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-top: 10px;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            overflow-x: auto;
        }
        
        pre {
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 0.9em;
            border-top: 1px solid #eee;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.8em;
            }
            
            .summary {
                grid-template-columns: repeat(2, 1fr);
                padding: 15px;
            }
            
            .results {
                padding: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 API 自动化测试报告</h1>
            <p>{{ report_time }}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card card-total">
                <h3>总测试数</h3>
                <div class="value">{{ summary.total_tests }}</div>
            </div>
            
            <div class="summary-card card-passed">
                <h3>通过 ✅</h3>
                <div class="value passed">{{ summary.passed_tests }}</div>
            </div>
            
            <div class="summary-card card-failed">
                <h3>失败 ❌</h3>
                <div class="value failed">{{ summary.failed_tests }}</div>
            </div>
            
            <div class="summary-card card-skipped">
                <h3>跳过 ⏭️</h3>
                <div class="value skipped">{{ summary.skipped_tests }}</div>
            </div>
            
            <div class="summary-card card-error">
                <h3>错误 ⚠️</h3>
                <div class="value error">{{ summary.error_tests }}</div>
            </div>
            
            <div class="summary-card card-duration">
                <h3>总耗时 ⏱️</h3>
                <div class="value">{{ "%.2f"|format(summary.total_duration) }}s</div>
            </div>
            
            <div class="summary-card card-rate">
                <h3>通过率 📊</h3>
                <div class="value">{{ "%.1f"|format(summary.success_rate) }}%</div>
            </div>
        </div>
        
        <div class="results">
            <h2>📋 详细结果</h2>
            
            {% for result in results %}
            <div class="test-case {{ 'active' if result.status.value == 'failed' else '' }}">
                <div class="test-case-header" onclick="this.parentElement.classList.toggle('active')">
                    <span class="test-case-name">{{ result.test_case_name }}</span>
                    <span class="test-case-status status-{{ result.status.value }}">
                        {{ result.status.value }}
                        ({{ "%.2f"|format(result.total_duration) }}s)
                    </span>
                </div>
                
                <div class="test-case-details">
                    {% if result.step_results %}
                    {% for step in result.step_results %}
                    <div class="step">
                        <div class="step-header">
                            <span class="step-name">📍 {{ step.step_name }}</span>
                            <span class="step-info">
                                状态: <strong class="{{ step.status.value }}">{{ step.status.value }}</strong>
                                | 耗时: {{ "%.3f"|format(step.duration) }}s
                            </span>
                        </div>
                        
                        {% if step.request_result and step.request_result.request %}
                        <div class="request-info">
                            <strong>请求:</strong><br>
                            <pre>{{ step.request_result.request.method }} {{ step.request_result.request.url }}</pre>
                            {% if step.request_result.request|attr('json') or step.request_result.request|attr('data') %}
                            <pre>{{ step.request_result.request.json or step.request_result.request.data | tojson(indent=2) }}</pre>
                            {% endif %}
                        </div>
                        {% endif %}
                        
                        {% if step.assertions_results %}
                        <div class="assertions">
                            <strong>断言结果:</strong>
                            {% for assertion in step.assertion_results %}
                            <div class="assertion-item assertion-{{ 'passed' if assertion.success else 'failed' }}">
                                {{ '✓' if assertion.success else '✗' }} {{ assertion.message }}
                                {% if not assertion.success %}
                                <br>&nbsp;&nbsp;期望: {{ assertion.expected }}<br>
                                &nbsp;&nbsp;实际: {{ assertion.actual }}
                                {% endif %}
                            </div>
                            {% endfor %}
                        </div>
                        {% endif %}
                        
                        {% if step.error_message %}
                        <div style="color: #dc3545; margin-top: 10px;">
                            <strong>错误:</strong> {{ step.error_message }}
                        </div>
                        {% endif %}
                    </div>
                    {% endfor %}
                    {% endif %}
                    
                    {% if result.error_message %}
                    <div style="color: #dc3545; margin-top: 15px; padding: 15px; background: #fff; border-radius: 5px;">
                        <strong>❌ 错误信息:</strong><br>
                        {{ result.error_message }}
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="footer">
            <p>Generated by API Test Agent | {{ report_time }}</p>
        </div>
    </div>
    
    <script>
        document.querySelectorAll('.test-case').forEach(tc => {
            if (tc.querySelector('.status-failed')) {
                tc.classList.add('active');
            }
        });
    </script>
</body>
</html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            summary=summary,
            results=summary.results,
            report_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML 报告已生成: {filepath}")
        return filepath
    
    def generate_json_report(
        self,
        summary: ExecutionSummary,
        filename: str = None
    ) -> str:
        """生成 JSON 报告"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        report_data = {
            'summary': {
                'total_tests': summary.total_tests,
                'passed_tests': summary.passed_tests,
                'failed_tests': summary.failed_tests,
                'skipped_tests': summary.skipped_tests,
                'error_tests': summary.error_tests,
                'success_rate': summary.success_rate,
                'total_duration': summary.total_duration,
                'start_time': summary.start_time.isoformat() if summary.start_time else None,
                'end_time': summary.end_time.isoformat() if summary.end_time else None
            },
            'results': []
        }
        
        for result in summary.results:
            test_case_data = {
                'name': result.test_case_name,
                'status': result.status.value,
                'duration': result.total_duration,
                'error_message': result.error_message,
                'steps': []
            }
            
            for step in result.step_results or []:
                step_data = {
                    'name': step.step_name,
                    'status': step.status.value,
                    'duration': step.duration,
                    'error_message': step.error_message,
                    'assertions': []
                }
                
                if step.assertion_results:
                    for assertion in step.assertion_results:
                        step_data['assertions'].append({
                            'success': assertion.success,
                            'message': assertion.message,
                            'expected': assertion.expected,
                            'actual': assertion.actual
                        })
                
                test_case_data['steps'].append(step_data)
            
            report_data['results'].append(test_case_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON 报告已生成: {filepath}")
        return filepath
    
    def generate_console_summary(self, summary: ExecutionSummary):
        """输出控制台摘要"""
        print("\n" + "="*80)
        print("🧪 API 自动化测试报告")
        print("="*80)
        print(f"\n📊 执行摘要:")
        print(f"   总测试数:    {summary.total_tests}")
        print(f"   ✅ 通过:     {summary.passed_tests}")
        print(f"   ❌ 失败:     {summary.failed_tests}")
        print(f"   ⏭️ 跳过:     {summary.skipped_tests}")
        print(f"   ⚠️ 错误:     {summary.error_tests}")
        print(f"   📈 通过率:    {summary.success_rate:.2f}%")
        print(f"   ⏱️ 总耗时:    {summary.total_duration:.2f}s")
        
        if summary.failed_tests > 0:
            print(f"\n❌ 失败的测试用例:")
            for result in summary.results:
                if not result.passed:
                    print(f"   - {result.test_case_name}")
                    if result.error_message:
                        print(f"     错误: {result.error_message}")
        
        print("\n" + "="*80 + "\n")