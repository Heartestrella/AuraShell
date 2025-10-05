import xml.etree.ElementTree as ET
import json
import re
import inspect
from typing import Optional, Dict, Any, Callable

class AIMCPManager:
    """
    Manages parsing, handling, and execution of AI MCP tool usage requests.
    """
    def __init__(self):
        self.mcp_tool_pattern = re.compile(r'<use_mcp_tool>.*?</use_mcp_tool>', re.DOTALL)
        self.tools: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def _generate_schema_from_signature(self, handler: Callable[..., Any]) -> Dict[str, Any]:
        sig = inspect.signature(handler)
        properties = {}
        required = []
        type_mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object"
        }
        doc = handler.__doc__
        if doc:
            properties = doc
        else:
            for param in sig.parameters.values():
                param_type = type_mapping.get(param.annotation, "any")
                properties[param.name] = {
                    "type": param_type,
                }
                if param.default != None:
                    properties[param.name]["default"] = param.default
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def register_tool_handler(self, server_name: str, tool_name: str, handler: Callable[..., Any], description: str, schema: Optional[Dict[str, Any]] = None, auto_approve: bool = False):
        if server_name not in self.tools:
            self.tools[server_name] = {}
        if schema is None:
            schema = self._generate_schema_from_signature(handler)
            schema = schema.get("properties", {})
        self.tools[server_name][tool_name] = {
            "handler": handler,
            "description": description,
            "schema": schema,
            "auto_approve": auto_approve
        }

    def execute_tool(self, server_name: str, tool_name: str, arguments:str) -> Dict[str, Any]:
        server = self.tools.get(server_name)
        if not server:
            return {"status": "error", "content": f"Server '{server_name}' is not registered."}
        tool = server.get(tool_name)
        if not tool:
            return {"status": "error", "content": f"Tool '{tool_name}' is not registered for server '{server_name}'."}
        handler = tool.get("handler")
        if not handler:
            return {"status": "error", "content": f"Handler for tool '{tool_name}' is missing."}
        try:
            sig = inspect.signature(handler)
            try:
                while not isinstance(arguments, dict):
                    arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = { "args": arguments }
            bound_args = sig.bind(**arguments)
            return handler(*bound_args.args, **bound_args.kwargs)
        except Exception as e:
            return {"status": "error", "content": str(e)}

    def parse_mcp_tool_use(self, message: str) -> Optional[Dict[str, Any]]:
        match = self.mcp_tool_pattern.search(message)
        if not match:
            return None
        xml_content = match.group(0)
        try:
            root = ET.fromstring(xml_content)
            server_name_element = root.find('server_name')
            tool_name_element = root.find('tool_name')
            arguments_element = root.find('arguments')
            if server_name_element is None or tool_name_element is None or arguments_element is None:
                return None
            server_name = server_name_element.text.strip() if server_name_element.text else ""
            tool_name = tool_name_element.text.strip() if tool_name_element.text else ""
            try:
                arguments_text = arguments_element.text.strip() if arguments_element.text else "{}"
                arguments = arguments_text
            except json.JSONDecodeError:
                return None
            tool_info = self.tools.get(server_name, {}).get(tool_name, {})
            auto_approve = tool_info.get("auto_approve", False)
            return {
                "server_name": server_name,
                "tool_name": tool_name,
                "arguments": arguments,
                "auto_approve": auto_approve,
                "_xml_": xml_content
            }
        except ET.ParseError:
            return None
        except Exception:
            return None
