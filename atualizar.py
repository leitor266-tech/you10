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
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as e:
        erro = e.read().decode("utf-8", errors="ignore")
        print("ERRO DA API:", e.code)
        print(erro)
        return None

    except Exception as e:
        print("ERRO:", e)
        return None


def extrair_video_id(url):
    if not url:
        return None

    # https://www.youtube.com/watch?v=XXXXXXXXXXX
    match = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", url)

    if match:
        return match.group(1)

    # https://youtu.be/XXXXXXXXXXX
    match = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", url)

    if match:
        return match.group(1)

    # https://www.youtube.com/embed/XXXXXXXXXXX
    match = re.search(r"/embed/([A-Za-z0-9_-]{11})", url)

    if match:
        return match.group(1)

    return None


def extrair_handle(url):
    if not url:
        return None

    match = re.search(
        r"youtube\.com/@([^/?]+)",
        url
    )

    if match:
        return "@" + match.group(1)

    return None


def encontrar_canal(handle):

    print("Buscando:", handle)

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


def encontrar_live(channel_id):

    print("Procurando live ativa...")

    resultado = api_get(
        "search",
        {
            "part": "snippet",
            "channelId": channel_id,
            "type": "video",
            "eventType": "live",
            "maxResults": 5
        }
    )

    if not resultado:
        return None

    itens = resultado.get("items", [])

    if not itens:
        print("Nenhuma live ativa.")
        return None

    for item in itens:

        video_id = item.get("id", {}).get("videoId")

        if video_id:

            titulo = item.get(
                "snippet",
                {}
            ).get(
                "title",
                ""
            )

            print("LIVE ENCONTRADA!")
            print("Título:", titulo)
            print("Video ID:", video_id)

            return video_id

    return None


def verificar_video(video_id):

    print("Verificando vídeo:", video_id)

    resultado = api_get(
        "videos",
        {
            "part": "snippet,liveStreamingDetails",
            "id": video_id
        }
    )

    if not resultado:
        return False

    itens = resultado.get("items", [])

    if not itens:
        return False

    video = itens[0]

    live = video.get(
        "liveStreamingDetails",
        {}
    )

    # Se possui actualStartTime, a transmissão começou.
    if live.get("actualStartTime"):

        # Se existe endTime, já terminou.
        if live.get("actualEndTime"):
            return False

        return True

    return False


def processar_canal(canal):

    nome = canal.get(
        "nome",
        "Canal"
    )

    url = canal.get(
        "url",
        ""
    )

    print("")
    print("================================")
    print("CANAL:", nome)
    print("URL:", url)
    print("================================")

    # ------------------------------------------------
    # Caso a URL já tenha um videoId
    # ------------------------------------------------

    video_id = extrair_video_id(url)

    if video_id:

        print(
            "Video ID encontrado na URL:",
            video_id
        )

        if verificar_video(video_id):

            canal["videoId"] = video_id
            canal["online"] = True

            print("LIVE ATIVA!")

        else:

            canal["videoId"] = ""
            canal["online"] = False

            print("Vídeo não está ao vivo.")

        return

    # ------------------------------------------------
    # Caso seja URL @handle/live
    # ------------------------------------------------

    handle = extrair_handle(url)

    if not handle:

        print("Não foi possível encontrar o handle.")

        canal["videoId"] = ""
        canal["online"] = False

        return

    channel_id = encontrar_canal(handle)

    if not channel_id:

        canal["videoId"] = ""
        canal["online"] = False

        return

    # ------------------------------------------------
    # Procurar transmissão ativa
    # ------------------------------------------------

    video_id = encontrar_live(channel_id)

    if video_id:

        canal["videoId"] = video_id
        canal["online"] = True

        print("CANAL ONLINE!")

    else:

        canal["videoId"] = ""
        canal["online"] = False

        print("CANAL OFFLINE.")


# ====================================================
# INÍCIO
# ====================================================

if not API_KEY:
    raise Exception(
        "YOUTUBE_API_KEY não encontrada."
    )


# Ler JSON

with open(
    JSON_FILE,
    "r",
    encoding="utf-8"
) as arquivo:

    dados = json.load(arquivo)


# Processar categorias

for categoria in dados.get(
    "categorias",
    []
):

    canais = categoria.get(
        "canais",
        []
    )

    for canal in canais:

        processar_canal(canal)


# Salvar JSON

with open(
    JSON_FILE,
    "w",
    encoding="utf-8"
) as arquivo:

    json.dump(
        dados,
        arquivo,
        ensure_ascii=False,
        indent=2
    )


print("")
print("================================")
print("ATUALIZAÇÃO CONCLUÍDA")
print("================================")
