import argparse
import os
import subprocess

from notion_helper import NotionHelper
from weread_api import WeReadApi

from utils import (
    get_callout,
    get_heading,
    get_number,
    get_number_from_result,
    get_quote,
    get_rich_text_from_result,
    get_table_of_contents,
)


def get_bookmark_list(page_id, bookId):
    """获取我的划线"""
    filter = {
        "and": [
            {"property": "书籍", "relation": {"contains": page_id}},
            {"property": "blockId", "rich_text": {"is_not_empty": True}},
        ]
    }
    results = notion_helper.query_all_by_book(
        notion_helper.bookmark_database_id, filter
    )
    dict1 = {
        get_rich_text_from_result(x, "bookmarkId"): get_rich_text_from_result(
            x, "blockId"
        )
        for x in results
    }
    dict2 = {get_rich_text_from_result(x, "blockId"): x.get("id") for x in results}
    bookmarks = weread_api.get_bookmark_list(bookId)
    for i in bookmarks:
        if i.get("bookmarkId") in dict1:
            i["blockId"] = dict1.pop(i.get("bookmarkId"))
    for blockId in dict1.values():
        notion_helper.delete_block(blockId)
        notion_helper.delete_block(dict2.get(blockId))
    return bookmarks


def append_blocks(page_id, bookmark_list):
    print(f"划线数{len(bookmark_list)}")
    before_block_id = ""
    block_children = notion_helper.get_block_children(page_id)
    if len(block_children) > 0 and block_children[0].get("type") == "table_of_contents":
        before_block_id = block_children[0].get("id")
    else:
        response = notion_helper.append_blocks(
            block_id=page_id, children=[get_table_of_contents()]
        )
        before_block_id = response.get("results")[0].get("id")
    blocks = []
    sub_contents = []
    l = []
    for bookmark in bookmark_list:
        if len(blocks) == 100:
            results = append_blocks_to_notion(page_id, blocks, before_block_id, sub_contents)
            before_block_id = results[-1].get("blockId")
            l.extend(results)
            blocks.clear()
            sub_contents.clear()
            blocks.append(content_to_block(bookmark))
            sub_contents.append(bookmark)
        elif "blockId" in bookmark:
            if len(blocks) > 0:
                l.extend(
                    append_blocks_to_notion(page_id, blocks, before_block_id, sub_contents)
                )
                blocks.clear()
                sub_contents.clear()
            before_block_id = bookmark["blockId"]
        else:
            blocks.append(content_to_block(bookmark))
            sub_contents.append(bookmark)

    if len(blocks) > 0:
        l.extend(append_blocks_to_notion(page_id, blocks, before_block_id, sub_contents))
    for index, value in enumerate(l):
        print(f"正在插入第{index + 1}条划线，共{len(l)}条")
        if "bookmarkId" in value:
            notion_helper.insert_bookmark(page_id, value)
        else:
            notion_helper.insert_chapter(page_id, value)


def content_to_block(bookmark):
    return get_callout(
        bookmark.get("markText", ""),
        bookmark.get("style"),
        bookmark.get("colorStyle"),
        bookmark.get("reviewId"),
    )


def append_blocks_to_notion(page_id, blocks, after, contents):
    response = notion_helper.append_blocks_after(
        block_id=page_id, children=blocks, after=after
    )
    results = response.get("results")
    l = []
    for index, content in enumerate(contents):
        result = results[index]
        content["blockId"] = result.get("id")
        l.append(content)
    return l


if __name__ == "__main__":
    try:
        subprocess.run(["pip", "install", "requests"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"安装 requests 模块时出错: {e}")

    parser = argparse.ArgumentParser()
    options = parser.parse_args()
    branch = os.getenv("REF").split("/")[-1]
    repository = os.getenv("REPOSITORY")
    weread_api = WeReadApi()
    notion_helper = NotionHelper()
    notion_books = notion_helper.get_all_book()
    books = weread_api.get_notebooklist()
    print(len(books))
    if books is not None:
        for index, book in enumerate(books):
            bookId = book.get("bookId")
            title = book.get("book").get("title")
            sort = book.get("sort")
            if bookId not in notion_books:
                continue
            if sort == notion_books.get(bookId).get("Sort"):
                continue
            pageId = notion_books.get(bookId).get("pageId")
            print(f"正在同步《{title}》的划线,一共{len(books)}本，当前是第{index + 1}本。")
            bookmark_list = get_bookmark_list(pageId, bookId)
            append_blocks(pageId, bookmark_list)
