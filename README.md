# 项目名称: FLYsecAgent

这是一个基于大语言模型和MCP（Model-Controller-Plugin）和Rag架构的网络安全智能助手项目。它旨在通过自然语言交互，帮助用户执行渗透测试任务、查询安全信息、分析流量包等。

## 功能特性

- **自然语言交互**: 用户可以通过自然语言向AI助手提问和下达指令。
- **MCP服务器集成**: 通过 `mcp.json` 配置文件，可以灵活集成和管理多个MCP服务器，扩展助手的能力。
- **工具调用**: AI助手能够根据用户请求，调用配置的MCP服务器提供的工具（例如：nmap, gobuster, fofa, tavily-search等）。
- **对话历史记忆**: 支持多轮对话，能够记住之前的交互内容。
- **流式输出**: AI的回答可以流式输出，提供更好的用户体验。
- **知识库增强 (可选)**: 支持通过本地知识库Rag（`knowledge_base_docs`目录）来增强AI的回答质量。
- **可配置模型**: 支持配置不同的语言模型参数。

## 安装指南

1.  **克隆仓库**:
    ```bash
    git clone https://github.com/hnking-star/FlySecAgent.git
    cd agent
    ```

2.  **创建并激活虚拟环境** (推荐):
    ```bash
    python -m venv .venv
    ```
    -   Windows:
        ```bash
        .venv\Scripts\activate
        ```
    -   macOS/Linux:
        ```bash
        source .venv/bin/activate
        ```

3.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **安装 `uv` (重要)**:
    本项目使用 `uv` 作为 Python 包的运行器和部分场景下的安装器。
    -   `start.bat` 脚本会自动尝试为您安装 `uv`。
    -   如果您希望手动安装或在其他环境中使用，可以运行：
        ```bash
        pip install uv
        ```
        或者参考 `uv` 的官方文档进行安装。
    确保 `uv` 已成功安装并可以从命令行调用。

## 使用方法

1.  **配置MCP服务器**: 
    修改 `mcp.json` 文件，根据您的环境和需求配置MCP服务器。确保每个服务器的启动命令和参数正确无误。例如，您可能需要更新 `TAVILY_API_KEY` 或其他服务器特定的路径/参数。

2.  **准备知识库 (可选)**:
    如果您希望使用知识库增强功能，请将相关的文本文件（例如 `.txt`）放入 `knowledge_base_docs` 文件夹中。

3.  **运行主程序**:
    ```bash
    python main.py
    ```
    程序启动后，您可以根据提示输入您的问题或指令。

## 文件结构

```
agent/
├── .venv/                  # Python虚拟环境 (被.gitignore忽略)
├── knowledge_base_docs/    # 知识库文档存放目录
│   └── ...
├── .gitignore              # Git忽略文件配置
├── main.py                 # 主程序入口
├── mcp.json                # MCP服务器配置文件
├── rag_embedding.py        # RAG嵌入相关 (如果使用)
├── rag_split.py            # RAG文本分割相关 (如果使用)
├── README.md               # 项目说明文件
├── requirements.txt        # Python依赖列表
├── LICENSE                 # 项目许可证
└── ... (其他脚本或配置文件)
```

## 配置文件 (`mcp.json`)

此文件用于定义AI助手可以连接和使用的MCP服务器。每个服务器条目应包含:
-   `name`: 服务器的唯一名称。
-   `params`: 启动服务器所需的参数，通常包括 `command` 和 `args`。
-   `cache_tools_list`: 是否缓存工具列表。

**示例服务器配置**:
```json
{
  "name": "tavily-search",
  "params": {
    "command": "uv",
    "args": [
      "--directory",
      "F:\\ai\\mcp\\mcp_tool\\mcp-server-tavily",
      "run",
      "tavily-search"
    ],
    "env": {
      "TAVILY_API_KEY": "your_tavily_api_key_here",
      "PYTHONIOENCODING": "utf-8"
    }
  },
  "cache_tools_list": true
}
```
请确保将示例中的路径和API密钥替换为您自己的配置。

## 贡献指南

欢迎对此项目做出贡献！如果您有任何建议或发现任何问题，请随时提交 Issue 或 Pull Request。

## 许可证

本项目采用 [MIT 许可证](LICENSE)。"# FlySecAgent" 
