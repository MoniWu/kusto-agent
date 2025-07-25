from azure.identity import InteractiveBrowserCredential
import requests
from config import get_config
from openai import AzureOpenAI
import click
from langchain.document_loaders import TextLoader


config = get_config()

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=5001)
@click.option('--config-path', 'config_path', default=None, help='Path to custom configuration file')
def main(host: str, port: int, config_path: str = None):
    #Login to your microsoft account
    credential = InteractiveBrowserCredential()
    token = credential.get_token("https://api.applicationinsights.io/.default").token

    app_id = config.get('appinsight',{})["app_id"]
    #Check for Azure OpenAI configuration
    azure_config = config.get('azure_openai', {})
    
    while True:
        user_input = input("Please input the requirement for the query:")
        if user_input.strip().lower() == "exit":
            print("Exiting...")
            break
        
        print("Generating kusto query......")
        
        kusto_query = generate_kusto_query(user_input,azure_config)
        print(f"The generated kusto query is:\n {kusto_query}")

        execute_kusto_query(kusto_query,token,app_id)        

def generate_kusto_query(user_input,azure_config):
    client = AzureOpenAI(
        api_key= azure_config["api_key"],
        api_version= azure_config["api_version"],
        azure_endpoint= azure_config["endpoint"]
    )

    # Load the kusto schema
    loader = TextLoader("kusto_schema.txt")
    documents = loader.load()

    # Split it into chunks
    # text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    # docs = text_splitter.split_documents(documents)

    # # To do Transfer docs into embedding 
    # embeddings = AzureOpenAIEmbeddings(
    #     deployment=azure_config["deployment_name"],
    #     openai_api_key=azure_config["api_key"],
    #     openai_api_version=azure_config["api_version"]
    # )

    # db = FAISS.from_documents(docs, embeddings)
    # db.save_local("kusto_vector_index")

    # relevant_docs = db.similarity_search(query, k=3)
    # schema = "\n".join([doc.page_content for doc in relevant_docs])
    
    prompt =f'''
            You are an expert in Azure Application Insights, you can translate the user requirement into Kusto query.The message should be 
            a query that can be execute immediately and no other useless word is needed.
            Here is the Kusto schema:
            {documents}
            The columns appear in the query must satisfy the schema,Distinguish between upper and lower case of English
            '''
    response = client.chat.completions.create(
        model = azure_config['deployment_name'],  # 可用 gpt-3.5-turbo
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_input}
        ]
    )
    query = response.choices[0].message.content
    return query

def execute_kusto_query(query,token,app_id):
    url = f"https://api.applicationinsights.io/v1/apps/{app_id}/query?query={query}"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(url, headers=headers).json()
        table = response['tables'][0]
        print("The query result is:\n")
        for row in table['rows']:
            print(row)
    except Exception as e:
        print(f"Get exception:{e}")


if __name__ == "__main__":
    main()

# 编写 Kusto 查询语句
# query = """
# customEvents
# | limit 2
# | order by timestamp desc
# """
# url = f"https://api.applicationinsights.io/v1/apps/{app_id}/query?query={query}"

# headers = {
#     "Authorization": f"Bearer {token}"
# }

# try:
#     response = requests.get(url, headers=headers).json()
#     table = response['tables'][0]
#     for row in table['rows']:
#         print(row)
# except Exception as e:
#     print(f"Get exception:{e}")


# 解析结果
# if response.status == LogsQueryStatus.SUCCESS:
#     table = response.tables[0]
#     for row in table.rows:
#         print(row)
# else:
#     print("查询失败：", response.status)