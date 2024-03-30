import json

import requests

# https://api.russpass.ru/search/portal/catalog/placesAndEvents
# https://api.russpass.ru/cmsapi/v2_event?id=6606678dc3ed3ab0cc45c8da&language=ru
RUSSPASS_HOST = "https://api.russpass.ru"


def get_items(total_pages: int, page: int = 31) -> list[dict]:
    req = {"filters": [], "page": page}
    headers = {"Rqid": "09b86041-4c70-4458-a377-d8ff89e4b172", "Content-Language": "ru"}
    res = requests.post(url=f"{RUSSPASS_HOST}/search/portal/catalog/placesAndEvents", json=req, headers=headers)
    res_data = res.json()
    res_objects = res_data["objects"] if "objects" in res_data else []
    if res_objects and page < total_pages:
        next_objects = get_items(total_pages, page=page+1)
        return res_objects + next_objects
    return res_objects


def get_item_info(item_id: str) -> dict:
    res = requests.get(url=f"{RUSSPASS_HOST}/cmsapi/v2_event?id={item_id}&language=ru")
    return res.json()


def get_items_descriptions(total_pages: int) -> list[dict]:
    items = get_items(total_pages=total_pages)
    item_ids = [i["objectId"] for i in items]
    result_descriptions = []
    for item_id in item_ids:
        item_info = get_item_info(item_id=item_id)
        if "item" not in item_info:
            if 'code' in item_info:
                print("Error", item_info['code'])
            else:
                print("WTF", item_info)
            continue
        title = item_info["item"]["title"]
        description = item_info["item"]["description"]
        cities = [c["title"] for c in item_info.get("cities", [])]
        regions = [c["title"] for c in item_info.get("regions", [])]
        tags = [c["title"] for c in item_info.get("tags", [])]
        full_text = f"{title}. Город: {', '.join(cities)}, регион: {', '.join(regions)}. Теги: {', '.join(tags)}. {description}"
        result_description = {"id": item_id, "title": title, "description": description,"cities": cities, "regions": regions, "tags": tags, "full_text": full_text}
        result_descriptions.append(result_description)
    return result_descriptions


def print_random_descriptions():
    print()


if __name__ == "__main__":
    TOTAL_PAGES = 100
    results = get_items_descriptions(total_pages=TOTAL_PAGES)
    with open("result_descriptions3.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
