import json


def _getJSON(path):
    with open(path) as json_file:
        return json.loads(json.load(json_file))
    
def _dump(path, data):
    with open(path, 'w', encoding='utf8') as outfile:
        json.dump(data, outfile, indent=2, ensure_ascii=False)

def _valid_img_type(img_name):
    valid_types = [
        '.tif', '.tiff', '.jpg', '.jpeg', '.jpe', '.jif,', '.jfif', '.jfi',  '.gif', '.png', '.svg'
    ]
    for t in valid_types:
        if img_name.lower().endswith(t):
            return True
    return False

def _validated_limit(limit, offset, list_len):
    res = limit if limit else list_len - offset
    return min(res, list_len - offset)

def _get_translated_file_label(language_code):
    # to identify the correct translation, follow these steps:
    # 1) open some Wikipedia article in required language
    # 2) click on any image to get a full-window preview
    # 3) look-up on the url page in the browser. The required translation
    #   would be just after the last "/", such as in this example it will be "Archivo:"
    # https://es.wikipedia.org/wiki/A_Christmas_Carol#/media/Archivo:Charles.jpg
    # Please note that you need to include semicolon (":") at the end as well
    lang2label = {
        'en': 'File:',
        'uk': 'Файл:',
        'es': 'Archivo:',
        'de': 'Datei:',
        'fr': 'Fichier:',
        'pl': 'Plik:',
        'it': 'File:',
        'pt': 'Ficheiro:',
        'ru': 'Файл:',
        'ja': 'ファイル:',
        'zh': 'File:',
    }

    if language_code not in lang2label:
        raise Exception('{} language is currently unsupported. To fix this,'\
            'please add corresponding translation to @lang2label dict above')

    return lang2label[language_code]