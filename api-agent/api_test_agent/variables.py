import re
import json
import copy
from typing import Any, Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class VariableManager:
    """变量管理器"""
    
    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.env_variables: Dict[str, Any] = {}
        self.global_variables: Dict[str, Any] = {}
        
        logger.info("变量管理器初始化完成")
    
    def set(self, name: str, value: Any):
        """设置变量"""
        self.variables[name] = value
        logger.debug(f"设置变量: {name} = {value}")
    
    def get(self, name: str, default: Any = None) -> Any:
        """获取变量"""
        if name in self.variables:
            return self.variables[name]
        if name in self.env_variables:
            return self.env_variables[name]
        if name in self.global_variables:
            return self.global_variables[name]
        return default
    
    def delete(self, name: str):
        """删除变量"""
        if name in self.variables:
            del self.variables[name]
            logger.debug(f"删除变量: {name}")
    
    def clear(self):
        """清除所有变量（保留全局和环境变量）"""
        self.variables.clear()
        logger.debug("清除所有变量")
    
    def set_env_variable(self, name: str, value: Any):
        """设置环境变量"""
        self.env_variables[name] = value
    
    def set_global_variable(self, name: str, value: Any):
        """设置全局变量"""
        self.global_variables[name] = value
    
    def update(self, variables: Dict[str, Any]):
        """批量更新变量"""
        self.variables.update(variables)
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有变量（合并后）"""
        all_vars = {}
        all_vars.update(self.global_variables)
        all_vars.update(self.env_variables)
        all_vars.update(self.variables)
        return all_vars
    
    def substitute_variables(self, text: str) -> str:
        """替换文本中的变量引用"""
        if not isinstance(text, str):
            return text
        
        pattern = r'\$\{([^}]+)\}'
        
        def replace_var(match):
            var_name = match.group(1)
            value = self.get(var_name)
            
            if value is None:
                logger.warning(f"未找到变量: {var_name}")
                return match.group(0)
            
            return str(value)
        
        result = re.sub(pattern, replace_var, text)
        max_iterations = 10
        
        for _ in range(max_iterations):
            new_result = re.sub(pattern, replace_var, result)
            if new_result == result:
                break
            result = new_result
        
        return result
    
    def substitute_in_dict(self, data: Any) -> Any:
        """递归替换字典中的所有变量"""
        if isinstance(data, str):
            return self.substitute_variables(data)
        elif isinstance(data, dict):
            return {k: self.substitute_in_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.substitute_in_dict(item) for item in data]
        else:
            return data
    
    def extract_from_response(
        self,
        response_data: Any,
        expression: str,
        from_response: str = "body"
    ) -> Any:
        """从响应中提取值"""
        try:
            if from_response == "body":
                obj = response_data.get('body', {})
            elif from_response == "headers":
                obj = response_data.get('headers', {})
            elif from_response == "status_code":
                return response_data.get('status_code')
            else:
                obj = response_data
            
            parts = expression.split('.')
            current = obj
            
            for part in parts:
                if '[' in part and ']' in part:
                    key = part.split('[')[0]
                    index_str = part.split('[')[1].split(']')[0]
                    
                    if key and key != '':
                        current = current[key]
                    current = current[int(index_str)]
                elif part:
                    if isinstance(current, dict):
                        current = current[part]
                    else:
                        raise ValueError(f"无法访问: {part}")
            
            return current
            
        except Exception as e:
            logger.error(f"提取值失败 - 表达式: {expression}, 错误: {e}")
            return None
    
    def export_to_file(self, file_path: str):
        """导出变量到文件"""
        import json
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.get_all(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"变量已导出到: {file_path}")
    
    def import_from_file(self, file_path: str):
        """从文件导入变量"""
        import json
        
        with open(file_path, 'r', encoding='utf-8') as f:
            variables = json.load(f)
        
        self.update(variables)
        logger.info(f"从文件导入变量: {file_path}")