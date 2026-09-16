import json
import os
import urllib.parse
import urllib.request
import urllib.error

JSON_FILE = "canaisyout.json"
API_KEY = os.environ.get("YOUTUBE_API_KEY")


def requisicao(url):
    try:
        with urllib.request.urlopen(url) as resposta:
            return json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        erro = e.read().decode("utf-8", errors="ignore")
        print("Erro HTTP:", e.code, erro)
        return None
    except Exception as e:
        print("Erro:", e)
        return None


def pegar_handle(url):
    try:
        parsed = urllib.parse.urlparse(url)
        partes = [p for p in parsed.path.split("/") if p]

        for parte in partes:
            if parte.startswith("@"):
                return parte

    except Exception:
        pass

    return None


def encontrar_video(url):
    handle = pegar_handle(url)

    if not handle:
        print("Handle não encontrado:", url)
        return None

    print("Consultando:", handle)

    # 1 - Descobrir o canal pelo handle
    params = urllib.parse.urlencode({
        "part": "id",
        "forHandle": handle[1:],
        "key": API_KEY
    })

    resposta = requisicao(
        "https://www.googleapis.com/youtube/v3/channels?" + params
    )

    if not resposta or not resposta.get("items"):
        print("Canal não encontrado:", handle)
        return None

    channel_id = resposta["items"][0]["id"]

    print("Channel ID:", channel_id)

    # 2 - Procurar live atual
    params = urllib.parse.urlencode({
        "part": "snippet",
        "channelId": channel_id,
        "eventType": "live",
        "type": "video",
        "maxResults": 5,
        "key": API_KEY
    })

    resposta = requisicao(
        "https://www.googleapis.com/youtube/v3/search?" + params
    )

    if not resposta:
        return None

    itens = resposta.get("items", [])

    for item in itens:
        video_id = item.get("id", {}).get("videoId")

        if video_id:
            titulo = item.get("snippet", {}).get("title", "")
            print("LIVE encontrada:", titulo)
            print("Video ID:", video_id)

            return video_id

    print("Nenhuma live encontrada:", handle)

    return None


def processar(lista):
    for canal in lista:

        nome = canal.get("nome", "Canal")
        url = canal.get("url", "")

        if not url:
            continue

        print("")
        print("==============================")
        print("CANAL:", nome)
        print("==============================")

        video_id = encontrar_video(url)

        if video_id:
            canal["videoId"] = video_id
            canal["online"] = True
        else:
            canal["videoId"] = ""
            canal["online"] = False


# Verificar chave
if not API_KEY:
    raise Exception("YOUTUBE_API_KEY não encontrada nos Secrets do GitHub.")


# Ler JSON
with open(JSON_FILE, "r", encoding="utf-8") as arquivo:
    dados = json.load(arquivo)


# Processar categorias
if isinstance(dados, dict):

    categorias = dados.get("categorias", [])

    for categoria in categorias:

        canais = categoria.get("canais", [])

        if isinstance(canais, list):
            processar(canais)


# Processar lista simples, se existir
if isinstance(dados, dict):

    canais = dados.get("canais", [])

    if isinstance(canais, list):
        processar(canais)


# Salvar
with open(JSON_FILE, "w", encoding="utf-8") as arquivo:

    json.dump(
        dados,
        arquivo,
        ensure_ascii=False,
        indent=2
    )

print("")
print("==============================")
print("JSON ATUALIZADO COM SUCESSO")
print("==============================")
