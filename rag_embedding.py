import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

client = OpenAI(
    api_key=os.getenv("EMBEDDING_API_KEY"),  # 从环境变量读取Embedding API密钥
    base_url=os.getenv("OPENAI_BASE_URL")  # 从环境变量读取base_url
)

completion = client.embeddings.create(
    model="text-embedding-v3",
    input='衣服的质量杠杠的，很漂亮，不枉我等了这么久啊，喜欢，以后还来这里买',
    dimensions=1024, # 指定向量维度（仅 text-embedding-v3 支持该参数）
    encoding_format="float"
)

response_json = completion.model_dump_json()
embedding_data = json.loads(response_json)
embedding_array = embedding_data['data'][0]['embedding']
print(len(embedding_array))
print(type(embedding_array))
print("提取的embedding数组：", embedding_array)