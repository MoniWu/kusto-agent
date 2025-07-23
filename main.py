from azure.identity import InteractiveBrowserCredential
import requests
from agent.config import get_config
from openai import AzureOpenAI


config = get_config()

def main():
    #Login to your microsoft account
    credential = InteractiveBrowserCredential()
    token = credential.get_token("https://api.applicationinsights.io/.default").token

    app_id = config.get('appinsight',{})["app_id"]
    #Check for Azure OpenAI configuration
    azure_config = config.get('azure_openai', {})
    print(azure_config)
    
    user_input = input("Please input the requirement for the query:")
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

    prompt ='''
            You are en expert in Azure Application Insights, you can translate the user requirement into Kusto query.The message should be 
            a query that can be execute immediately and no other useless word is needed.
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