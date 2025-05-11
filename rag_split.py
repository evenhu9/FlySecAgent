#from curses import color_content
from ollama import chat,Message
from ollama import embeddings
import os
import json
from openai import OpenAI
import numpy as np
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 设置numpy打印选项，显示完整数组
np.set_printoptions(threshold=np.inf)

client = OpenAI(
    api_key=os.getenv("EMBEDDING_API_KEY"),  # 从环境变量读取Embedding API密钥
    base_url=os.getenv("OPENAI_BASE_URL")  # 从环境变量读取base_url
)

import os # Added for directory operations

class Kb:
    def __init__(self, dirpath):  # 读取目录中的所有文档
        all_content = ""
        if not os.path.isdir(dirpath):
            print(f"Error: {dirpath} is not a valid directory.")
            self.docs = []
            self.embedss = np.array([])
            return

        for filename in os.listdir(dirpath):
            filepath = os.path.join(dirpath, filename)
            if os.path.isfile(filepath):
                try:
                    with open(filepath, 'r', encoding="utf-8") as f:
                        all_content += f.read() + "\n"  # Add a newline to separate file contents
                except Exception as e:
                    print(f"Error reading file {filepath}: {e}")
        
        if not all_content.strip():
            print(f"Warning: No content found in directory {dirpath}.")
            self.docs = []
            self.embedss = np.array([])
            return

        self.docs = self.split_content(all_content)  # 将所有文档内容合并后分割
        if self.docs:
            self.embedss = self.encode(self.docs)
        else:
            self.embedss = np.array([])

    @staticmethod
    def split_content(content,max_length=5000):
        chuncks=[]
        for i in range(0,len(content),max_length):
            chuncks.append(content[i:i+max_length])
        return chuncks


    def encode(self,texts):
          embeds=[]
          for text in texts:
            completion = client.embeddings.create(
            model="text-embedding-v3",
            input=text  ,
            dimensions=1024, # 指定向量维度（仅 text-embedding-v3 支持该参数）
            encoding_format="float"
            )
            response_json = completion.model_dump_json()
            embedding_data = json.loads(response_json)
            embedding_array = embedding_data['data'][0]['embedding']
            embeds.append(embedding_array)
          return np.array(embeds)

   
    @staticmethod #相似度
    def similarity(A,B):
        dot_product=np.dot(A,B)
        norm_A=np.linalg.norm(A)
        norm_B=np.linalg.norm(B)
        similarity=dot_product/(norm_A*norm_B)
        return similarity
     
    def search(self,query):
        max_similarity=0
        max_similarity_index=0
        query_embedding=self.encode([query])[0]
        for idx,te in enumerate(self.embedss):
            similarity=self.similarity(query_embedding,te)
            if similarity>max_similarity:
                max_similarity=similarity
                max_similarity_index=idx
        return self.docs[max_similarity_index]
     

if __name__ == "__main__":
    # Example usage: Create a dummy directory and file for testing
    test_kb_dir = "knowledge_base_docs_test"
    if not os.path.exists(test_kb_dir):
        os.makedirs(test_kb_dir)
    with open(os.path.join(test_kb_dir, "test_doc.txt"), 'w', encoding='utf-8') as f:
        f.write("This is a test document for security audit information.")
    
    kb = Kb(test_kb_dir)
    if kb.docs: # Check if docs were loaded
        #for doc in kb.docs:
        # print("========================================================")
        # print(doc)

        #for e in kb.embedss:
        # print(e)
        result = kb.search("security audit")
        print(f"Search result: {result}")
    else:
        print("Knowledge base is empty or failed to load.")
    
    # Clean up dummy directory and file
    # import shutil
    # if os.path.exists(test_kb_dir):
    #     shutil.rmtree(test_kb_dir)