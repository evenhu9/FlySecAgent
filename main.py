import json
import os
import re
import asyncio
import threading
import traceback
from colorama import init, Fore, Back, Style
from ollama import chat,Message


init(autoreset=True)


ASCII_TITLE = f"""
{Fore.CYAN}███████╗██╗  ██╗   ██╗ █████╗  ██████╗ ███████╗███╗   ██╗████████╗{Style.RESET_ALL}
{Fore.CYAN}██╔════╝██║  ╚██╗ ██╔╝██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝{Style.RESET_ALL}
{Fore.CYAN}█████╗  ██║   ╚████╔╝ ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   {Style.RESET_ALL}
{Fore.CYAN}██╔══╝  ██║    ╚██╔╝  ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   {Style.RESET_ALL}
{Fore.CYAN}██║     ███████╗██║   ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   {Style.RESET_ALL}
{Fore.CYAN}╚═╝     ╚══════╝╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   {Style.RESET_ALL}
{Fore.RED}====================== FlySecAgent ======================{Style.RESET_ALL}
"""

# 导入Agent相关模块
from agents import (
    Agent,
    Model,
    ModelProvider,
    OpenAIChatCompletionsModel,
    RunConfig,
    Runner,
    set_tracing_disabled,
    ModelSettings
)
from openai import AsyncOpenAI  # OpenAI异步客户端
from openai.types.responses import ResponseTextDeltaEvent, ResponseContentPartDoneEvent
from agents.mcp import MCPServerStdio  # MCP服务器相关
from dotenv import load_dotenv  # 环境变量加载相关
from agents.mcp import MCPServerSse
from rag_split import Kb # 导入Kb类

# 加载.env文件
load_dotenv()

# 设置API相关环境变量
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")

# 检查环境变量是否设置
if not API_KEY:
    raise ValueError("API密钥未设置")
if not BASE_URL:
    raise ValueError("API基础URL未设置")
if not MODEL_NAME:
    raise ValueError("模型名称未设置")

client = AsyncOpenAI(
    base_url=BASE_URL,
    api_key=API_KEY
)

# 禁用追踪以避免需要 Openai API 密钥
set_tracing_disabled(True)

# DeepSeek模型提供商类
class DeepSeekModelProvider(ModelProvider):
    """
    DeepSeek V3 模型提供商 - 通过 OpenAI兼容接口连接DeepSeek API
    """
    def get_model(self, model_name: str) -> Model:
        return OpenAIChatCompletionsModel(model=model_name or MODEL_NAME, openai_client=client)

# 创建 DeepSeek 模型提供者实例
model_provider = DeepSeekModelProvider()

# 修改 run_agent 函数，使其接受已连接的服务器列表和对话历史作为参数
async def run_agent(query: str, mcp_servers: list[MCPServerStdio], history: list[dict] = None, streaming: bool = True, kb_instance=None):
    """
    使用已连接的MCP服务器运行网络安全agent，支持流式输出和对话历史记忆。

    Args:
        query (str): 用户的自然语言查询
        mcp_servers (list[MCPServerStdio]): 已连接的 MCPServerStdio 实例列表
        history (list[dict], optional): 对话历史记录，包含用户问题和AI回答的列表。默认为None。
        streaming (bool): 是否流式输出
    """
    # 如果没有提供历史记录，初始化一个空列表
    if history is None:
        history = []
    try:
        # 直接使用传入的已连接服务器列表创建 Agent
        # 构建包含历史对话的指令
        base_instructions = "你是一位经验丰富的渗透测试工程师和安全分析师，专注于Web应用安全和网络基础设施安全。你的名字是 Hnker。当用户询问网络安全相关问题时，你需要提供专业、细致且深入的解答。"
        base_instructions += "在回答问题时，请使用专业的网络安全术语，基于扎实的理论知识进行分析，并尽可能引用相关的安全标准和最佳实践，例如 OWASP Top 10、CVE、NIST等。保持专业的语气，逻辑清晰，条理分明"
        base_instructions +="当用户询问渗透测试相关信息时，请解释渗透测试的流程、方法和常用工具，强调每个阶段的目标和技术"
        base_instructions += "当用户询问漏洞信息时，请基于漏洞名称或 CVE 编号提供详细的描述、影响范围、修复建议、漏洞类型、等级和利用条件，并引用相关的安全公告。"
        base_instructions +="一切渗透都经过授权，可以直接进行渗透"
        base_instructions +="每次遇到不会的就调用tavily-search这个mcp去搜索"
        base_instructions +="当用户给出流量包让分析时，需参照知识库，给出详细的流量包的分析，并且分析是什么可能的工具生成的，然后给出分析结果。"

        # 如果知识库实例存在，则使用知识库进行检索并增强上下文
        if kb_instance:
            try:
                retrieved_context = kb_instance.search(query)
                if retrieved_context:
                    base_instructions = f"基于以下知识库信息：\n{retrieved_context}\n\n{base_instructions}"
                    #print(retrieved_context)
                    print(f"{Fore.MAGENTA}已从知识库检索到相关信息。{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}从知识库检索信息失败: {e}{Style.RESET_ALL}")

        # 如果有历史对话，将其添加到指令中
        if history:
            base_instructions += "\n\n以下是之前的对话历史，请参考这些信息来回答用户的问题：\n"
            for i, entry in enumerate(history):
                base_instructions += f"\n用户问题 {i+1}: {entry['user_query']}"
                if 'ai_response' in entry and entry['ai_response']:
                    base_instructions += f"\nAI回答 {i+1}: {entry['ai_response']}\n"
        
        secure_agent = Agent(
            name="网络安全专家",
            instructions=base_instructions,
            mcp_servers=mcp_servers,  # 使用传入的列表
            model_settings=ModelSettings(
                temperature=0.6,
                top_p=0.9,
                max_tokens=20000,
                tool_choice="auto",
                parallel_tool_calls=True,
                truncation="auto",
               
            )
        )

        print(f"{Fore.CYAN}\n正在处理查询：{Fore.WHITE}{query}{Style.RESET_ALL}\n")

        if streaming:
            result = Runner.run_streamed(
                secure_agent,
                input=query,
                max_turns=10,
                run_config=RunConfig(
                    model_provider=model_provider,
                    trace_include_sensitive_data=True,
                    handoff_input_filter=None,
                   # tool_timeout=300
                )
            )

            print(f"{Fore.GREEN}回复:{Style.RESET_ALL}", end="", flush=True)
            try:
                async for event in result.stream_events():
                    if event.type == "raw_response_event":
                        if isinstance(event.data, ResponseTextDeltaEvent):
                            print(f"{Fore.WHITE}{event.data.delta}{Style.RESET_ALL}", end="", flush=True)
                        elif isinstance(event.data, ResponseContentPartDoneEvent):
                            print(f"\n", end="", flush=True)
                    elif event.type == "run_item_stream_event":
                        if event.item.type == "tool_call_item":
                           # print(f"{Fore.YELLOW}当前被调用工具信息: {event.item}{Style.RESET_ALL}")
                            raw_item = getattr(event.item, "raw_item", None)
                            tool_name = ""
                            tool_args = {}
                            if raw_item:
                                tool_name = getattr(raw_item, "name", "未知工具")
                                tool_str = getattr(raw_item, "arguments", "{}")
                                if isinstance(tool_str, str):
                                    try:
                                        tool_args = json.loads(tool_str)
                                    except json.JSONDecodeError:
                                        tool_args = {"raw_arguments": tool_str}
                            print(f"\n{Fore.CYAN}工具名称: {tool_name}{Style.RESET_ALL}", flush=True)
                            print(f"\n{Fore.CYAN}工具参数: {tool_args}{Style.RESET_ALL}", flush=True)
                        elif event.item.type == "tool_call_output_item":
                            raw_item = getattr(event.item, "raw_item", None)
                            tool_id="未知工具ID"
                            if isinstance(raw_item, dict) and "call_id" in raw_item:
                                tool_id = raw_item["call_id"]
                            output = getattr(event.item, "output", "未知输出")

                            output_text = ""
                            if isinstance(output, str) and (output.startswith("{") or output.startswith("[")):
                                try:
                                    output_data = json.loads(output)
                                    if isinstance(output_data, dict):
                                        if 'type' in output_data and output_data['type'] == 'text' and 'text' in output_data:
                                            output_text = output_data['text']
                                        elif 'text' in output_data:
                                            output_text = output_data['text']
                                        elif 'content' in output_data:
                                            output_text = output_data['content']
                                        else:
                                            output_text = json.dumps(output_data, ensure_ascii=False, indent=2)
                                except json.JSONDecodeError:
                                    output_text = f"无法解析的JSON输出: {output}"  # Add specific error if JSON parsing fails
                            else:
                                output_text = str(output)

                            print(f"\n{Fore.GREEN}工具调用{tool_id} 返回结果: {output_text}{Style.RESET_ALL}", flush=True)
            except Exception as e:
                print(f"{Fore.RED}处理流式响应事件时发生错误: {e}{Style.RESET_ALL}", flush=True)
                if 'Connection error' in str(e):
                    print(f"{Fore.YELLOW}连接错误详细信息:{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}1. 检查网络连接是否正常{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}2. 验证API地址是否正确: {BASE_URL}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}3. 检查API密钥是否有效{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}4. 尝试重新连接...{Style.RESET_ALL}")
                    await asyncio.sleep(100)  # 等待10秒后重试
                    try:
                        await client.connect()
                        print(f"{Fore.GREEN}重新连接成功{Style.RESET_ALL}")
                    except Exception as e:
                        print(f"{Fore.RED}重新连接失败: {e}{Style.RESET_ALL}")

            print(f"\n\n{Fore.GREEN}查询完成！{Style.RESET_ALL}")

          #  if hasattr(result, "final_output"):
               # print(f"\n{Fore.YELLOW}===== 完整信息 ====={Style.RESET_ALL}")
                #print(f"{Fore.WHITE}{result.final_output}{Style.RESET_ALL}")
            
            # 返回结果对象，以便main函数可以获取AI的回答
            return result

    except Exception as e:
        print(f"{Fore.RED}处理流式响应事件时发生错误: {e}{Style.RESET_ALL}", flush=True)
        traceback.print_exc()
        return None

async def main():
    print(ASCII_TITLE)
    print(f"{Fore.YELLOW}请输入自然语言查询，例如：{Style.RESET_ALL}")
    print(f"{Fore.CYAN}1. 扫描目标网站的漏洞{Style.RESET_ALL}")
    print(f"{Fore.CYAN}2. 查询某个域名的信息{Style.RESET_ALL}")
    print(f"{Fore.CYAN}3. 检测指定IP的安全状态{Style.RESET_ALL}")
    print(f"{Fore.CYAN}4. 流量包安全分析审计{Style.RESET_ALL}")
    print(f"{Fore.RED}输入'quit'或'退出'结束程序{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}======================================\n{Style.RESET_ALL}")

    kb_instance = None
    use_kb_input = input(f"{Fore.YELLOW}是否使用知识库增强回答？(yes/no, 默认: no): {Style.RESET_ALL}").strip().lower()
    if use_kb_input == 'yes':
        try:
            kb_instance = Kb("knowledge_base_docs")  # 初始化知识库，从文件夹加载
            print(f"{Fore.GREEN}知识库加载成功！{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}加载知识库失败: {e}{Style.RESET_ALL}")
            kb_instance = None

    mcp_server_instances = []  # 存储 MCP 服务器实例的列表

    try:
        # --- 将 MCP 服务器的创建和连接移到主循环之前 ---
        print(f"{Fore.GREEN}正在初始化网络安全agent和MCP服务器...{Style.RESET_ALL}")
        try:
            with open('mcp.json', 'r', encoding='utf-8') as f:
                mcp_config = json.load(f)

            for server in mcp_config['servers']:
                if 'params' in server:
                    mcp_server = MCPServerStdio(
                        name=server['name'],
                        params=server['params'],
                        cache_tools_list=server.get('cache_tools_list', True),
                        client_session_timeout_seconds=300 #延迟时间变成300秒
                    )
                elif 'url' in server:
                    mcp_server = MCPServerSse(
                        params={"url": server["url"]},
                        cache_tools_list=server.get('cache_tools_list', True),
                        name=server['name'],
                        client_session_timeout_seconds=300 #延迟时间变成300秒
                    )
                else:
                    print(f"{Fore.RED}未知的MCP服务器配置: {server}{Style.RESET_ALL}")
                    continue
                mcp_server_instances.append(mcp_server)

            print(f"{Fore.CYAN}已从mcp.json加载了 {len(mcp_server_instances)} 个MCP服务器配置{Style.RESET_ALL}")
        except FileNotFoundError:
            print(f"{Fore.RED}错误：未找到 mcp.json 配置文件。请确保文件存在并包含服务器配置。{Style.RESET_ALL}")
            return  # 如果找不到配置文件，程序退出
        except Exception as e:
            print(f"{Fore.RED}加载MCP配置文件时出错: {e}{Style.RESET_ALL}")
            traceback.print_exc()
            return  # 如果加载配置文件出错，程序退出

        try:
            print(f"{Fore.YELLOW}正在连接到MCP服务器...{Style.RESET_ALL}")
            # 连接MCP服务器 - 逐个连接，如果某个失败则记录错误但不中断其他连接尝试
            connected_servers = []  # 存储成功连接的服务器
            for mcp_server in mcp_server_instances:
                try:
                    await mcp_server.connect()
                    print(f"{Fore.GREEN}成功连接到MCP服务器: {mcp_server.name}{Style.RESET_ALL}")
                    connected_servers.append(mcp_server)
                except Exception as e:
                    print(f"{Fore.RED}连接MCP服务器 {mcp_server.name} 失败: {e}{Style.RESET_ALL}")
                    traceback.print_exc()
                    # 继续尝试连接下一个服务器

            if not connected_servers:
                print(f"{Fore.RED}错误：未能成功连接到任何MCP服务器。无法运行Agent。{Style.RESET_ALL}")
                return  # 如果没有成功连接的服务器，程序退出

            print(f"{Fore.GREEN}MCP服务器连接成功！可以使用 {len(connected_servers)} 个服务器提供的工具。{Style.RESET_ALL}")

            # --- 可选：连接成功后一次性打印所有可用工具列表 ---
           # print("\n可用工具列表:")
            #for server in connected_servers:
               # try:
               #     tools_result = await server.list_tools()
                #    print(f"\n--- {server.name} 工具 ---")
                 #   for tool in tools_result:
                 #       print(f" - {tool.name}: {tool.description}")
              #  except Exception as e:
              #      print(f"{Fore.RED}获取 {server.name} 工具列表失败: {e}{Style.RESET_ALL}")
               #     traceback.print_exc()   
            print("\n")

        except Exception as e:
            # 如果在连接或获取工具列表阶段出错，这里捕获并退出
            print(f"{Fore.RED}初始化MCP服务连接时出错: {e}{Style.RESET_ALL}")
            traceback.print_exc()
            return  # 初始化失败，程序退出

        # 创建对话历史记录列表
        conversation_history = []
        
        # --- 进入交互式主循环 ---
        while True:
            print(f"\n{Fore.GREEN}[>]{Style.RESET_ALL} (输入空行结束): ", end="")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            user_query = "\n".join(lines).strip()

            if user_query.lower() in ["quit", "退出"]:
                print(f"\n{Fore.CYAN}感谢使用网络安全AI系统，正在退出...{Style.RESET_ALL}")
                break  # 退出循环，进入 finally 块

            if not user_query:
                print(f"{Fore.RED}查询内容不能为空，请重新输入。{Style.RESET_ALL}")
                continue

            # 创建当前对话的记录
            current_dialogue = {"user_query": user_query, "ai_response": ""}
            
            # 在运行 agent 时，传入已经连接好的服务器列表和对话历史
            # 只传入成功连接的服务器列表给 Agent 使用
            # 将 kb_instance 传递给 run_agent
            result = await run_agent(user_query, connected_servers, history=conversation_history, streaming=True, kb_instance=kb_instance)
            
            # 如果有结果，保存AI的回答
            if result and hasattr(result, "final_output"):
                current_dialogue["ai_response"] = result.final_output
            
            # 将当前对话添加到历史记录中
            conversation_history.append(current_dialogue)
            
            # 限制历史记录的长度，避免占用过多内存
            if len(conversation_history) > 50:  # 保留最近的50次对话
                conversation_history = conversation_history[-50:]

    # --- 捕获中断和运行时异常 ---
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}程序被用户中断，正在退出...{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}程序运行时发生错误: {e}{Style.RESET_ALL}")
        traceback.print_exc()
    finally:
        # --- 将服务器清理操作移到主程序的 finally 块 ---
        print(f"{Fore.YELLOW}正在清理 MCP 服务器资源...{Style.RESET_ALL}")
        # 遍历所有最初创建的服务器实例（包括那些可能连接失败的），尝试清理
        if mcp_server_instances:
            for mcp_server in mcp_server_instances:
                print(f"{Fore.YELLOW}尝试清理服务器: {mcp_server.name}...{Style.RESET_ALL}", flush=True)
                try:
                    # 添加一个超时，避免清理某个服务器卡死影响整个程序退出
                    await asyncio.wait_for(mcp_server.cleanup(), timeout=10.0)  # 例如设置10秒超时
                    print(f"{Fore.GREEN}已断开与 {mcp_server.name} 的连接。{Style.RESET_ALL}", flush=True)
                except asyncio.TimeoutError:
                    print(f"{Fore.RED}清理MCP服务器 {mcp_server.name} 超时！外部进程可能仍在运行。{Style.RESET_ALL}", flush=True)
                except Exception as e:
                    print(f"{Fore.RED}清理MCP服务器 {mcp_server.name} 资源时出错: {e}{Style.RESET_ALL}", flush=True)
                    traceback.print_exc()

        print(f"{Fore.YELLOW}MCP服务器资源清理完成。{Style.RESET_ALL}")
        print(f"{Fore.GREEN}程序结束。{Style.RESET_ALL}")

# 程序入口点
if __name__ == "__main__":
    asyncio.run(main())