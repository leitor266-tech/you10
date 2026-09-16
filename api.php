<?php

/*
=========================================================
RESOLVEDOR DE LIVE DO YOUTUBE
=========================================================

Este arquivo recebe:

    api.php?url=https://www.youtube.com/@CazeTV/live

E retorna:

{
  "ok": true,
  "videoId": "XXXXXXXXXXX",
  "title": "...",
  "channelId": "...",
  "thumbnail": "..."
}

IMPORTANTE:
Coloque sua chave da YouTube Data API v3 abaixo.
NUNCA coloque essa chave no index.html.
=========================================================
*/

header("Content-Type: application/json; charset=utf-8");
header("Access-Control-Allow-Origin: *");
header("Cache-Control: no-store");


// =======================================================
// SUA CHAVE DA YOUTUBE DATA API V3
// =======================================================

$API_KEY = "AIzaSyC75jFj0MJuBD2iaKjDALWKscc8tXadUSg";


// =======================================================
// CONFIGURAÇÃO
// =======================================================

$CACHE_SECONDS = 60;


// =======================================================
// FUNÇÕES
// =======================================================

function resposta($dados, $codigo = 200)
{
    http_response_code($codigo);

    echo json_encode(
        $dados,
        JSON_UNESCAPED_UNICODE |
        JSON_UNESCAPED_SLASHES |
        JSON_PRETTY_PRINT
    );

    exit;
}


function youtubeApi($endpoint, $params)
{
    global $API_KEY;

    $params["key"] = $API_KEY;

    $url =
        "https://www.googleapis.com/youtube/v3/" .
        $endpoint .
        "?" .
        http_build_query($params);

    $ch = curl_init($url);

    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 15,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_USERAGENT => "MinhaTVOnline/1.0"
    ]);

    $body = curl_exec($ch);

    $erro = curl_error($ch);

    $http = curl_getinfo($ch, CURLINFO_HTTP_CODE);

    curl_close($ch);

    if ($body === false) {
        resposta([
            "ok" => false,
            "erro" => "Erro de conexão com o YouTube.",
            "detalhes" => $erro
        ], 502);
    }

    $json = json_decode($body, true);

    if (!is_array($json)) {
        resposta([
            "ok" => false,
            "erro" => "Resposta inválida da API do YouTube."
        ], 502);
    }

    if ($http >= 400 || isset($json["error"])) {

        $mensagem =
            $json["error"]["message"]
            ?? "Erro desconhecido da API do YouTube.";

        resposta([
            "ok" => false,
            "erro" => $mensagem,
            "youtube_http" => $http
        ], 502);
    }

    return $json;
}


function extrairHandle($url)
{
    $path = parse_url($url, PHP_URL_PATH);

    if (!$path) {
        return "";
    }

    if (preg_match(
        '~/@([A-Za-z0-9._-]+)~',
        $path,
        $m
    )) {
        return $m[1];
    }

    return "";
}


function extrairVideoId($url)
{
    $query = parse_url($url, PHP_URL_QUERY);

    if ($query) {

        parse_str($query, $params);

        if (!empty($params["v"])) {

            $id = $params["v"];

            if (preg_match(
                '/^[A-Za-z0-9_-]{11}$/',
                $id
            )) {
                return $id;
            }
        }
    }

    if (preg_match(
        '~youtu\.be/([A-Za-z0-9_-]{11})~',
        $url,
        $m
    )) {
        return $m[1];
    }

    return "";
}


function cacheArquivo($chave)
{
    return __DIR__ .
        "/cache_live_" .
        md5($chave) .
        ".json";
}


function lerCache($arquivo, $tempo)
{
    if (!file_exists($arquivo)) {
        return null;
    }

    if (
        time() -
        filemtime($arquivo)
        > $tempo
    ) {
        return null;
    }

    $conteudo = file_get_contents($arquivo);

    if (!$conteudo) {
        return null;
    }

    $json = json_decode($conteudo, true);

    return is_array($json)
        ? $json
        : null;
}


function salvarCache($arquivo, $dados)
{
    @file_put_contents(
        $arquivo,
        json_encode(
            $dados,
            JSON_UNESCAPED_UNICODE |
            JSON_UNESCAPED_SLASHES
        ),
        LOCK_EX
    );
}


// =======================================================
// RECEBE URL
// =======================================================

$url = $_GET["url"] ?? "";

$url = trim($url);

if (!$url) {

    resposta([
        "ok" => false,
        "erro" => "URL não informada."
    ], 400);
}


// =======================================================
// 1. SE JÁ FOR watch?v=
// =======================================================

$videoIdDireto = extrairVideoId($url);

if ($videoIdDireto) {

    resposta([
        "ok" => true,
        "source" => "url",
        "videoId" => $videoIdDireto,
        "embed" =>
            "https://www.youtube.com/embed/" .
            $videoIdDireto
    ]);
}


// =======================================================
// 2. EXTRAI @HANDLE
// =======================================================

$handle = extrairHandle($url);

if (!$handle) {

    resposta([
        "ok" => false,
        "erro" =>
            "Não foi possível encontrar o @handle na URL."
    ], 400);
}


// =======================================================
// CACHE
// =======================================================

$cacheFile = cacheArquivo($handle);

$cache = lerCache(
    $cacheFile,
    $CACHE_SECONDS
);

if ($cache !== null) {

    resposta($cache);
}


// =======================================================
// 3. DESCOBRE CHANNEL ID
// =======================================================

$channelResponse = youtubeApi(
    "channels",
    [
        "part" => "id,snippet",
        "forHandle" => $handle
    ]
);


if (
    empty($channelResponse["items"]) ||
    empty($channelResponse["items"][0]["id"])
) {

    $resultado = [
        "ok" => false,
        "online" => false,
        "erro" =>
            "Canal não encontrado: @" . $handle
    ];

    salvarCache(
        $cacheFile,
        $resultado
    );

    resposta($resultado);
}


$channel =
    $channelResponse["items"][0];

$channelId =
    $channel["id"];


// =======================================================
// 4. PROCURA TRANSMISSÃO AO VIVO
// =======================================================

$liveResponse = youtubeApi(
    "search",
    [
        "part" => "snippet",
        "channelId" => $channelId,
        "eventType" => "live",
        "type" => "video",
        "maxResults" => 1
    ]
);


// =======================================================
// 5. CANAL OFFLINE
// =======================================================

if (
    empty($liveResponse["items"]) ||
    empty(
        $liveResponse["items"][0]["id"]["videoId"]
    )
) {

    $resultado = [
        "ok" => true,
        "online" => false,
        "handle" => $handle,
        "channelId" => $channelId,
        "message" =>
            "Este canal não possui uma transmissão ao vivo ativa."
    ];

    salvarCache(
        $cacheFile,
        $resultado
    );

    resposta($resultado);
}


// =======================================================
// 6. PEGOU A LIVE ATUAL
// =======================================================

$item =
    $liveResponse["items"][0];

$videoId =
    $item["id"]["videoId"];

$snippet =
    $item["snippet"]
    ?? [];

$titulo =
    $snippet["title"]
    ?? "Transmissão ao vivo";

$thumbnail =
    $snippet["thumbnails"]["high"]["url"]
    ?? $snippet["thumbnails"]["medium"]["url"]
    ?? $snippet["thumbnails"]["default"]["url"]
    ?? "";


$resultado = [
    "ok" => true,
    "online" => true,

    "handle" => $handle,

    "channelId" => $channelId,

    "videoId" => $videoId,

    "title" => $titulo,

    "thumbnail" => $thumbnail,

    "embed" =>
        "https://www.youtube.com/embed/" .
        $videoId
];


// =======================================================
// SALVA CACHE
// =======================================================

salvarCache(
    $cacheFile,
    $resultado
);


// =======================================================
// RETORNA
// =======================================================

resposta($resultado);
?>
