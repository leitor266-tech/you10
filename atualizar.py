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

        with urllib.request.urlopen(
            url,
            timeout=30
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as e:

        erro = e.read().decode(
            "utf-8",
            errors="ignore"
        )

        print("ERRO API:", e.code)
        print(erro)

        return None

    except Exception as e:

        print("ERRO:", e)

        return None


def extrair_video_id(url):

    if not url:
        return None

    # youtube.com/watch?v=XXXXXXXXXXX
    match = re.search(
        r"[?&]v=([A-Za-z0-9_-]{11})",
        url
    )

    if match:
        return match.group(1)

    # youtu.be/XXXXXXXXXXX
    match = re.search(
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        url
    )

    if match:
        return match.group(1)

    # youtube.com/embed/XXXXXXXXXXX
    match = re.search(
        r"/embed/([A-Za-z0-9_-]{11})",
        url
    )

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

    itens = resultado.get(
        "items",
        []
    )

    if not itens:

        print(
            "Canal não encontrado:",
            handle
        )

        return None

    channel_id = itens[0]["id"]

    print(
        "Channel ID:",
        channel_id
    )

    return channel_id


def encontrar_live(channel_id):

    print(
        "Procurando transmissão ativa..."
    )

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

    itens = resultado.get(
        "items",
        []
    )

    for item in itens:

        video_id = item.get(
            "id",
            {}
        ).get(
            "videoId"
        )

        if video_id:

            titulo = item.get(
                "snippet",
                {}
            ).get(
                "title",
                ""
            )

            print(
                "LIVE ENCONTRADA:",
                titulo
            )

            print(
                "Video ID:",
                video_id
            )

            return video_id

    print(
        "Nenhuma live ativa encontrada."
    )

    return None


def verificar_video(video_id):

    if not video_id:
        return False

    print(
        "Verificando vídeo:",
        video_id
    )

    resultado = api_get(
        "videos",
        {
            "part": "snippet,liveStreamingDetails",
            "id": video_id
        }
    )

    if not resultado:
        return False

    itens = resultado.get(
        "items",
        []
    )

    if not itens:
        return False

    video = itens[0]

    live = video.get(
        "liveStreamingDetails",
        {}
    )

    inicio = live.get(
        "actualStartTime"
    )

    fim = live.get(
        "actualEndTime"
    )

    if inicio and not fim:

        print(
            "LIVE ATIVA:",
            video_id
        )

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

    # ID que já estava salvo
    id_anterior = canal.get(
        "videoId",
        ""
    )

    print("")
    print("================================")
    print("CANAL:", nome)
    print("================================")

    # ------------------------------------------------
    # 1. Procurar live pelo canal
    # ------------------------------------------------

    handle = extrair_handle(url)

    if handle:

        channel_id = encontrar_canal(
            handle
        )

        if channel_id:

            novo_id = encontrar_live(
                channel_id
            )

            if novo_id:

                canal["videoId"] = novo_id
                canal["online"] = True

                print(
                    "NOVO ID SALVO:",
                    novo_id
                )

                return

    # ------------------------------------------------
    # 2. Se não encontrou nova live,
    #    testar o ID anterior
    # ------------------------------------------------

    if id_anterior:

        print(
            "Nenhuma live nova."
        )

        print(
            "Mantendo ID anterior:",
            id_anterior
        )

        if verificar_video(
            id_anterior
        ):

            canal["online"] = True

        else:

            canal["online"] = False

        # NÃO apagar o ID
        canal["videoId"] = id_anterior

        return

    # ------------------------------------------------
    # 3. Se a URL já tiver ID
    # ------------------------------------------------

    id_url = extrair_video_id(
        url
    )

    if id_url:

        canal["videoId"] = id_url

        if verificar_video(
            id_url
        ):

            canal["online"] = True

        else:

            canal["online"] = False

        return

    # ------------------------------------------------
    # 4. Não existe ID conhecido
    # ------------------------------------------------

    canal["videoId"] = ""
    canal["online"] = False

    print(
        "Nenhum ID disponível."
    )


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

    dados = json.load(
        arquivo
    )


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

        processar_canal(
            canal
        )


# Salvar

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
print("ATUALIZAÇÃO FINALIZADA")
print("================================")
