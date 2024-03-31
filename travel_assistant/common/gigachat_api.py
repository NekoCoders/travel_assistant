import uuid
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests


AUTH_DATA = "NTYyODlhYzQtM2QxMy00NGNhLThmM2EtYzdiY2RiYzgzZjJhOjBmZTE0NzI3LTg4MDYtNDhjYy04NzhiLWU4YjlhYzI2ZTcwYg=="


def create_access_token(auth_data=AUTH_DATA):
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

    payload = 'scope=GIGACHAT_API_PERS'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': str(uuid.uuid4()),
        'Authorization': f'Basic {auth_data}'
    }

    response = requests.request("POST", url, headers=headers, data=payload, verify=False).json()
    token = response["access_token"]

    return token


if __name__ == '__main__':
    print(create_access_token())