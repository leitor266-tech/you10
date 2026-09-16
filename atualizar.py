import json
import os
import urllib.parse
import urllib.request

JSON_FILE = "canaisyout.json"

API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not API_KEY:
    raise Exception("YOUTUBE_API_KEY não configurada")

with open(JSON_FILE, "r", encoding="utf-8") as f:
    dados = json.load(f)


def youtube_api(url):
    try:
        parsed = urllib.parse.urlparse(url)
        caminho = parsed.path.strip("/")

        if caminho.endswith("/live"):
            handle = caminho[:-5]

            if not handle.startswith("@"):
                return None

            params = urllib.parse.urlencode({
                "part": "id",
                "forHandle": handle[1:],
                "key": API_KEY
            })

            url_api = (
                "https://www.googleapis.com/youtube/v3/channels?"
                + params
            )

            with urllib.request.urlopen(url_api) as response:
                resultado = json.loads(response.read().decode())

            if not resultado.get("items"):
                return None

            channel_id = resultado["items"][0]["id"]

            params = urllib.parse.urlencode({
                "part": "snippet,liveStreamingDetails",
                "channelId": channel_id,
                "eventType": "live",
                "type": "video",
                "maxResults": "1",
                "key": API_KEY
            })

            url_api = (
                "https://www.googleapis.com/youtube/v3/search?"
                + params
            )

            with urllib.request.urlopen(url_api) as response:
                resultado = json.loads(response.read().decode())

            if not resultado.get("items"):
                return None

            return resultado["items"][0]["id"]["videoId"]

    except Exception as e:
        print("Erro:", e)

    return None


def processar_canais(lista):
    for canal in lista:
        url = canal.get("url", "")

        if url:
            video_id = youtube_api(url)

            if video_id:
                canal["videoId"] = video_id
                canal["online"] = True
                print("LIVE encontrada:", canal.get("nome"), video_id)
            else:
                canal["videoId"] = ""
                canal["online"] = False
                print("OFFLINE:", canal.get("nome"))

        else:
            canal["videoId"] = ""
            canal["online"] = False


if isinstance(dados, dict):

    if isinstance(dados.get("categorias"), list):

        for categoria in dados["categorias"]:
            if isinstance(categoria.get("canais"), list):
                processar_canais(categoria["canais"])

    if isinstance(dados.get("canais"), list):
        processar_canais(dados["canais"])


with open(JSON_FILE, "w", encoding="utf-8") as f:
    json.dump(
        dados,
        f,
        ensure_ascii=False,
        indent=2
    )

print("JSON atualizado com sucesso.")
