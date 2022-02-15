from os import truncate
from requests import get
from time import sleep
import json



class Bot:
    def __init__(self, token: str):
        print("Inicializando...")
        self.token = token

    def sendMessage(self, chatid:int,  message:str):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {
                "chat_id" :chatid,
                "text" : message,
                "parse_mode" : "HTML"
          }
        resp = get(url, params=data).text
        if json.loads(resp)['ok']:
            return True
        else:
            return False

    def getChats(self):
        with open("telegram.json", "r", encoding="utf-8") as f:
            data = json.loads(f.read())
            return data['chats']
    def sendall(self, message) -> None:
         with open("telegram.json", "r", encoding="utf-8") as f:
            data = json.loads(f.read())
            for chat in data['chats']:
                self.sendMessage(chat['id'], message)
    def getUpdates(self):
        offset = None
        with open("telegram.json", "r+") as f:
            data = json.loads(f.read())
            if data['lastUpdateId'] != None:
                offset = data['lastUpdateId']
            else:
                offset = json.loads(get(f"https://api.telegram.org/bot{self.token}/getUpdates").text)
                offset = offset['result'][-1]['update_id']
                data['lastUpdateId'] = offset
            url = f"https://api.telegram.org/bot{self.token}/getUpdates?offset={offset}"
            resp = get(url).text
            if json.loads(resp)['ok']:
                result = json.loads(resp)
                update_id = result['result'][-1]['update_id']
                message_from = result['result'][-1]['message']['from']['first_name']
                chat_id = result['result'][-1]['message']['chat']['id']
                message = result['result'][-1]['message']['text']
                if {"id" : chat_id } not in data['chats'] and message == "/init":
                    data['chats'].append({"id" : chat_id})
                    self.sendMessage(chat_id, f"Iniciando bot para: {message_from}")
                data['lastUpdateId'] = update_id
                f.seek(0)
                f.write(json.dumps(data, indent=4))
                f.truncate()
                return True
            else:
                return False

