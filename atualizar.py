import json
import os
import re
import urllib.parse
import urllib.request
import urllib.error

JSON_FILE = "canaisyout.json"
API_KEY = os.environ.get("YOUTUBE_API_KEY")


def api_get(endpoint, params):
    params["key"] = API_KEY

    url = "https://www.googleapis.com/youtube/v3/" + endpoint
    url += "?" + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as e:
        erro = e.read().decode("utf-8", errors="ignore")
        print("ERRO YOUTUBE:", e.code)
        print(erro)
        return None

    except Exception as e:
        print("ERRO:", e)
        return None


def extrair_video_id(url):

    if not url:
        return None

    # watch?v=XXXXXXXXXXX
    match = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", url)

    if match:
        return match.group(1)

    # youtu.be/XXXXXXXXXXX
    match = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", url)

    if match:
        return match.group(1)

    # /embed/XXXXXXXXXXX
    match = re.search(r"/embed/([A-Za-z0-9_-]{11})", url)

    if match:
        return match.group(1)

    return None


def extrair_handle(url):

    if not url:
        return None

    match = re.search(r"youtube\.com/@([^/?]+)", url)

    if match:
        return "@" + match.group(1)

    return None


def canal_por_handle(handle):

    print("Buscando canal:", handle)

    resultado = api_get(
        "channels",
        {
            "part": "id",
            "forHandle": handle
        }
    )

    if not resultado:
        return None

    itens = resultado.get("items", [])

    if not itens:
        print("Canal não encontrado:", handle)
        return None

    channel_id = itens[0]["id"]

    print("Channel ID:", channel_id)

    return channel_id


def procurar_live(channel_id):

    print("Procurando transmissão ativa...")

    resultado = api_get(
        "search",
        {
            "part": "snippet",
            "channelId": channel_id,
            "eventType": "live",
            "type": "video",
            "maxResults": 5
        }
    )

    if not resultado:
        return None

    itens = resultado.get("items", [])

    for item in itens:

        video_id = item.get("id", {}).get("videoId")

        if video_id:

            titulo = item.get("snippet", {}).get("title", "")

            print("LIVE ENCONTRADA!")
            print("Título:", titulo)
            print("Video ID:", video_id)

            return video_id

    print("Nenhuma transmissão ao vivo ativa foi encontrada.")

    return None


def processar_canal(canal):

    nome = canal.get("nome", "Canal")
    url = canal.get("url", "")

    print("")
    print("================================")
    print("CANAL:", nome)
    print("URL:", url)
    print("================================")

    # ------------------------------------------------
    # PRIMEIRO: se a URL já possui videoId
    # ------------------------------------------------

    video_id = extrair_video_id(url)

    if video_id:

        print("Video ID encontrado na URL:", video_id)

        canal["videoId"] = video_id
        canal["online"] = True

        return

    # ------------------------------------------------
    # SEGUNDO: descobrir pelo @handle
    # ------------------------------------------------

    handle = extrair_handle(url)

    if not handle:

        print("Não foi possível encontrar o @handle.")

        canal["videoId"] = ""
        canal["online"] = False

        return

    channel_id = canal_por_handle(handle)

    if not channel_id:

        canal["videoId"] = ""
        canal["online"] = False

        return

    # ------------------------------------------------
    # TERCEIRO: procurar live ativa
    # ------------------------------------------------

    video_id = procurar_live(channel_id)

    if video_id:

        canal["videoId"] = video_id
        canal["online"] = True

    else:

        canal["videoId"] = ""
        canal["online"] = False


# ====================================================
# INÍCIO
# ====================================================

if not API_KEY:

    raise Exception(
        "A secret YOUTUBE_API_KEY não foi encontrada."
    )


# Ler JSON

with open(JSON_FILE, "r", encoding="utf-8") as arquivo:

    dados = json.load(arquivo)


# Processar categorias

for categoria in dados.get("categorias", []):

    canais = categoria.get("canais", [])

    for canal in canais:

        processar_canal(canal)


# Salvar JSON

with open(JSON_FILE, "w", encoding="utf-8") as arquivo:

    json.dump(
        dados,
        arquivo,
        ensure_ascii=False,
        indent=2
    )


print("")
print("================================")
print("JSON ATUALIZADO COM SUCESSO")
print("================================")
