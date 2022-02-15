from time import sleep
from typing import  TypedDict
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import json
import requests
import re
from bs4 import BeautifulSoup
import src.telegrambot as telegrambot
from datetime import datetime

bot = telegrambot.Bot('TOKEN')
prematchSentList = [] # Lista de jogos que ainda não começaram
endingSentMatchList = [] # Lista de jogos que já começaram

# Tipando os dicionários
PlayerBigHistoryDict = TypedDict('PlayerBigHistoryDict',
{
    "name" : str,
    "wins" : int,
    "draws" : int,
    "goalspmatch" : float,
    "goalsconceded" : float,
})

GameDataDict = TypedDict('GameDataDict', 
{
    
    "type" : str,
    "team1" : TypedDict('Dict_T', {
            "name": str,
            "score" : int
        }),
        
    "team2": TypedDict('Dict_T', {
            "name": str,
            "score" : int
        }),
    "time" : TypedDict('Dict_T', {
                "minutes": int,
            "seconds" :  int
    }),

    "time_raw" : str,
    "market_count" : str
                        
})


headers = { # Header aceito pelo esoccer
    'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
    'accept': 'text/html, */*; q=0.01',
    'x-requested-with': 'XMLHttpRequest',
    'sec-ch-ua-mobile': '?0',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
    'sec-ch-ua-platform': '"Windows"',
    'origin': 'https://esoccerbet.com.br',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty',
    'referer': 'https://esoccerbet.com.br/',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'content-type': 'application/x-www-form-urlencoded',
    'cookie': '',
}

def longPlayerHistoric(player: str) -> dict:
    """
    Retorna um dicionário com as estatísticas
    dos últimos jogos de um Player específico
    """
    
    url = "https://esoccerbet.com.br/acao/player-search2.php"
    result = requests.post(url, headers=headers, data={"player": player, "time" : ""})
    result = json.loads(result.text)
    return {
        "name" : player,
        "wins" : result['venceuP'],
        "draws" : result['empatouP'],
        "goalspmatch" : float(result['golsFeitosP']),
        "goalsconceded" : float(result['golsTomadosP']),
    } 


def recentHistoric() -> list:
    """
    Retorna as últimas 100 partidas
    dos jogos de 8, 10 e 12 minutos.
    """
    
    esoccerrequest = requests.get("https://esoccerbet.com.br/")
    esoccerresult = BeautifulSoup(esoccerrequest.text, "html.parser")
    lastgames = esoccerresult.find_all("div", {"class" : "partida"})
    gamelist = []
    c = 0
    for _game in lastgames:
        print(c)
        c += 1
        players = _game.find_all("div", {"class" : "jogador"})
        p1 = players[0].find_all("a")[0].get_text()
        p2 = players[1].find_all("a")[0].get_text()
        placar = _game.find("div", {"class" : "placar"})
        placar = [n.get_text() for n in placar.find("span").find_all("span") if n.get_text() != "x"]
        singlegame = {"team1": {"name" : p1, "score" : int(placar[0])}, "team2": {"name" : p2, "score" : int(placar[1])}}
        gamelist.append(singlegame)
    return gamelist

def rules(game: GameDataDict, historic: list, htmlElement) -> None:
    """Função onde serão aplicadas as condições de
    envio de mensagens.
    """
    
    global ChromeDriver
    team1_historic = []
    team2_historic = []
    p1name = re.search(r"\(.*?\)", game['team1']['name']).group(0).replace("(", "").replace(")", "") # Nome do jogador1
    p2name = re.search(r"\(.*?\)", game['team2']['name']).group(0).replace("(", "").replace(")", "") # Nome do jogador2
    p1BigHistoric:PlayerBigHistoryDict = longPlayerHistoric(p1name)
    p2BigHistoric:PlayerBigHistoryDict = longPlayerHistoric(p2name)

    for gh1 in historic:
        if gh1['team1']['name'] in game['team1']['name'].lower() or gh1['team2']['name'] in game['team1']['name'].lower():
            team1_historic.append(gh1)
    for gh2 in historic:
        # print(f"gh2: {gh2['team2']['name'], game['team2']['name'].lower()}") TODO
        if gh2['team1']['name'] in game['team2']['name'].lower() or gh1['team2']['name'] in game['team2']['name'].lower():
            team2_historic.append(gh2)
    # print(team1_historic) TODO
    # print(team2_historic) TODO
    team1_historic = team1_historic[:10]
    team2_historic = team2_historic[:10]
    team1_statistics = {
        'wins' : 0,
        'average_match_goals' : 0,
        'average_team_goals' : 0
    }
    team2_statistics = {
        'wins' : 0,
        'average_match_goals' : 0,
        'average_team_goals' : 0
    }

    for _g in team1_historic:
        team1_statistics['average_match_goals'] += _g['team1']['score'] + _g['team2']['score']
        team1_statistics['average_team_goals'] += (_g['team1']['score'] if _g['team1']['name'] in game['team1']['name'].lower()\
            else _g['team2']['score'])
            
        if (_g['team1']['score'] > _g['team2']['score']) and _g['team1']['name'] in game['team1']['name'].lower():
            team1_statistics['wins'] += 1
        if (_g['team2']['score'] > _g['team1']['score']) and _g['team2']['name'] in game['team1']['name'].lower():
            team1_statistics['wins'] += 1

    for _g in team2_historic:
        team2_statistics['average_match_goals'] += _g['team1']['score'] + _g['team2']['score']
        team2_statistics['average_team_goals'] += (_g['team1']['score'] if _g['team1']['name'] in game['team2']['name'].lower()\
            else _g['team2']['score'])
        if (_g['team1']['score'] > _g['team2']['score']) and _g['team1']['name'] in game['team2']['name'].lower():
            team2_statistics['wins'] += 1
        if (_g['team2']['score'] > _g['team1']['score']) and _g['team2']['name'] in game['team2']['name'].lower():
            team2_statistics['wins'] += 1

    team1_statistics['average_team_goals'] /= (len(team1_historic) if len(team1_historic) > 0 else 1) # Média de gols do time1
    team2_statistics['average_team_goals'] /= (len(team2_historic) if len(team2_historic) > 0 else 1) # Média de gols do time2
    team1_statistics['average_match_goals'] /= (len(team1_historic) if len(team1_historic) > 0 else 1) # Média de gols dos jogos do time1
    team2_statistics['average_match_goals'] /= (len(team2_historic) if len(team2_historic) > 0 else 1) # Média de gols dos jogos do time2
    team1name = game['team1']['name']
    team1score = game['team1']['score']
    team2name = game['team2']['name']
    team2score = game['team2']['score']

    sleep(1)
    # wheelChartContainer = ChromeDriver.find_elements_by_class_name("ml-WheelChart_Container")[-1]
    # t1dangerAttacks = WebDriverWait(wheelChartContainer, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "ml-WheelChart_Team1Text"))).get_attribute("innerHTML")
    # t2dangerAttacks = WebDriverWait(wheelChartContainer, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "ml-WheelChart_Team2Text"))).get_attribute("innerHTML")
    # try:
    #     WebDriverWait(ChromeDriver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, "ipe-EventHeader_Breadcrumb"))).click()
    # except:
    #     WebDriverWait(ChromeDriver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, "ipe-EventHeaderBreadcrumb_BackButton"))).click()
    # TODO ÚLTIMOS JOGOS ENTRE ESSES DOIS TIMES
    if f"{game['team1']['name']} x {game['team2']['name']}" not in prematchSentList:
        # if game['time_raw'] == "00:00":
            # bot.sendall(f"Jogo prestes a começar: {game['team1']['name']} x {game['team2']['name']}")
        zerozero = True if game['team1']['score'] == 0 and game['team2']['score'] == 0 else False
        if abs(p1BigHistoric['wins'] - p2BigHistoric['wins']) >= 15: # Se a diferença de vitórias dos 100 últimos jogos de cada time entre eles for 15:
            if game['team1']['score'] == 0 and game['team2']['score'] == 0: # Se o jogo estiver 0x0
                playerNameResult = p1BigHistoric['name'] if p1BigHistoric['wins'] > p2BigHistoric['wins'] else p2BigHistoric['name']
                bot.sendall(f"Atenção!\nPara ganhar: {playerNameResult}")


        if max(p1BigHistoric['goalspmatch'], p2BigHistoric['goalspmatch']) >= 1.5 and game['team1']['score'] + game['team2']['score'] == 0:
            playerNameResult = p1BigHistoric['name'] if p1BigHistoric['goalspmatch'] > p2BigHistoric['goalspmatch'] else p2BigHistoric['name']
            bot.sendall(f"Atenção!\nMais que 1.5 gols para: {playerNameResult}")
        BothGoalsPerMatch = (p1BigHistoric['goalspmatch'] + p1BigHistoric['goalsconceded'] + p2BigHistoric['goalspmatch'] + p1BigHistoric['goalsconceded'])/2
        goalsPredict = ""
        if zerozero:
            if BothGoalsPerMatch > 4.00:
                goalsPredict += "Mais que 3.5"
            elif BothGoalsPerMatch > 3.00:
                goalsPredict += "Mais que 2.5"
            else:
                goalsPredict += "Menos que 2.5"
            if goalsPredict != "":
                bot.sendall(f"Atenção!\n{game['team1']['name']} {game['team1']['score']} x {game['team2']['score']} {game['team2']['name']}\n <b>{goalsPredict}<b> gols. ")



        prematchSentList.append(f"{game['team1']['name']} x {game['team2']['name']}")

        
        
    if f"{game['team1']['name']} x {game['team2']['name']}" not in endingSentMatchList:
        noMoreGoalsTime = 6 if "8" in game['type'] else 8 if "10" in game['type'] else 10
        if game['time']['minutes'] >= noMoreGoalsTime and zerozero:
            bot.sendall(f"Atenção!\nSem 1o gol: {p1BigHistoric['name']} x {p2BigHistoric['name']}")
        endingSentMatchList.append(f"{game['team1']['name']} x {game['team2']['name']}")
    print(f"Last Update: {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}"   )
    sleep(3)

ChromeDriver = webdriver.Chrome("../chromedriver/chromedriver.exe")
ChromeDriver.get("https://www.bet365.com/#/IP/B151") # URL onde conseguimos as listas de jogos
sleep(3)
while True:
    try:
        competitions = WebDriverWait(ChromeDriver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "ovm-CompetitionHeader_NameText")))
        competitiongames = WebDriverWait(ChromeDriver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "ovm-Competition_Fixtures")))
        sleep(1.5)
        hist = recentHistoric()
        for i, r in enumerate(competitions):
            if any(x in r.text for x in ["E-soccer - Live Arena", "E-soccer - Battle"]): # Filtrando jogos somente para FIFA
                games = WebDriverWait(competitiongames[i], 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "ovm-FixtureDetailsTwoWay_Wrapper")))
                
                for game in games:
                    data:list = game.text.split("\n")
                    if len(data) < 6:
                        data.insert(2, "00:00") 

                    rules(
                        {
                            "type" : r.text,
                            "team1" : 
                                {
                                    "name": data[0],
                                    "score" : int(data[4])
                                },
                            "team2":
                                {
                                    "name": data[1],
                                    "score" : int(data[5])
                                },
                            "time" :
                                {
                                    "minutes": int(data[2].split(":")[0]),
                                    "seconds" :  int(data[2].split(":")[1])
                                },
                            "time_raw" : data[2],
                            "market_count" : data[3]
                                }, hist, game) # Cria um dict com os dados do jogo e passa para checagem de regras
        sleep(60) # Intervalo de tempo entre as consultas
    except Exception as e:
        print(f"Aviso: {e}")
        continue

