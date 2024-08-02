import os
import requests
import json
import time
from notion_client import Client
from datetime import datetime

# 从环境变量获取 Notion API 密钥
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
client = Client(auth=NOTION_TOKEN)

# 从环境变量获取源数据库和目标数据库的 ID
SOURCE_DATABASE_ID = os.environ.get('SOURCE_DATABASE_ID')
TARGET_DATABASE_ID = os.environ.get('TARGET_DATABASE_ID')

def get_data_from_source_database():
    """
    从源数据库中获取数据
    """
    filter = {}
    results = client.databases.query(database_id=SOURCE_DATABASE_ID, filter=filter)
    return results

def write_data_to_target_database(data):
    """
    将数据写入目标数据库
    """
    for item in data:
        properties = {
            # 映射源数据的属性到目标数据库的属性
            "Title": item.get("Title", ""),
            "Content": item.get("Content", ""),
            #... 其他属性
        }
        client.pages.create(parent={"database_id": TARGET_DATABASE_ID}, properties=properties)

def main():
    data = get_data_from_source_database()
    write_data_to_target_database(data)

if __name__ == "__main__":
    main()
