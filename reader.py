import pywikibot
import json
import mwparserfromhell as mwp
import hashlib
import urllib
import re
import shutil
import time

from pathlib import Path
from pywikibot import pagegenerators
from urllib.request import urlretrieve
from html.parser import HTMLParser
from html.entities import name2codepoint
from os import listdir, stat
from os.path import isfile, join
from dataclasses import dataclass
from typing import Optional
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from urllib.parse import unquote

# for fetch_meta_captions_fast
import urllib.request
from bs4 import BeautifulSoup

KNOWN_ICONS = [
    'SPQRomani.svg', 'Status_iucn3.1_LC.svg', 'Bullseye1.png', 'OOjs_UI_icon_edit-ltr-progressive.svg',
    'Celestia.png', 'Kit_shorts_Crusadersshorts17b.png', 'Chess_xxt45.svg',
    'Flag_of_the_United_States_(1912-1959).svg', 'Chess_plt45.svg', 'Allosaurus_Jardin_des_Plantes.png',
    'Flag_of_Scotland.svg', 'Hockey_current_event.svg', 'Tudor_Ensign_1485-1603.svg',
    'Naval_ensign_of_the_Empire_of_Japan.svg', 'Blank_television_set.svg', 'Magic_Kingdom_castle.jpg',
    'Kit_body.svg', 'Naval_Ensign_of_the_United_Kingdom.svg', 'Flag_of_Italy.svg', 'PD-icon.svg',
    'Papapishu-Lab-icon-6.svg', 'NFPA_704.svg', 'California_480.svg', 'Flag_of_Finland.svg', 'Chess_xot45.svg',
    'Ella_—_John_Speed.JPG', 'Dagger-14-plain.png', 'Openstreetmap_logo.svg', 'Flag_of_Georgia_(U.S._state).svg',
    'Hertfordshire_UK_relief_location_map.jpg', 'Earth_Day_Flag.png', 'Flag_of_Austria.svg',
    'Oceania_(orthographic_projection).svg', 'Wikispecies-logo.svg', 'Flag_of_Australia_(converted).svg',
    'Battle_of_Blenheim_-_Penetration,_1730,_13_August_1704.gif', 'Nuvola_apps_package_games_strategy.png',
    'Flag_of_Great_Britain_(1707–1800).svg', 'Hessen_HG_flag.svg', 'Gold_medal_icon.svg', 'Kit_right_arm.svg',
    'Loudspeaker.svg', 'Stylised_Lithium_Atom.svg', 'Flag_of_Hesse.svg', 'Belgium_relief_location_map.jpg',
    'Pfeil_links.svg', 'Flag_of_Hanover_(1692).svg', 'Battle_of_Blenhiem_-_Explotation,_13_August_1704.gif',
    'Johnny-automatic-scales-of-justice.svg', 'Ginsberg-dylan.jpg', 'Status_EPBC_EN.svg',
    'Tom_Sawyer_1876_frontispiece.jpg', 'Flag_of_the_Soviet_Union.svg', 'Nobel_Prize.png', 'Flag_of_India.svg',
    'Chessboard480.svg', '..West_Bengal_Flag(INDIA).png', 'Commons-logo.svg', 'Open_Access_logo_PLoS_transparent.svg',
    'Flag_of_Australia.svg', 'Order_of_the_Bath_(ribbon).svg', 'Status_iucn3.1_EX.svg', 'Flag_of_Germany.svg',
    '046CupolaSPietro.jpg', 'Chess_kdt45.svg', 'Ecuador_relief_location_map.svg', 'Flag_of_Iran.svg',
    'Status_iucn3.1_blank.svg', 'Flag_of_the_Kingdom_of_Prussia_(1701-1750).svg', 'Wikisource-logo.svg',
    'Flag_of_the_United_States_(1848–1851).svg', 'Speaker_Icon.svg', 'Kit_shorts.svg', 'Flag_of_the_Czech_Republic.svg',
    'Chess_bdt45.svg', 'Heinkel_He_111_during_the_Battle_of_Britain.jpg', 'Gloriole_blur.svg',
    'Symbol_book_class2.svg', 'Books-aj.svg_aj_ashton_01.svg', 'Pyramidi_aavikolla.png', 'EC1835_C_cut.jpg',
    'Bohr-atom-PAR.svg', 'Quill_and_ink.svg', 'Façade_de_la_cathédrale_Saint-Pierre_de_Genève.jpg',
    'Chavundaraya_Poet_Handwriting.JPG', 'Socrates.png', 'Wikidata-logo.svg', 'Nome_deities_with_offerings.JPG.jpg',
    'Mergefrom.svg', 'Flag_of_Poland.svg', 'People_icon.svg', 'Flag_of_the_United_Kingdom.svg', 'Flag_of_Oklahoma.svg',
    'Flag_of_Portugal.svg', 'Flag_of_New_Zealand.svg', 'Chess_ndt45.svg', 'Flag_of_Denmark.svg', 'P_vip.svg',
    'Wikiversity-logo-Snorky.svg', 'All_Gizah_Pyramids.jpg', 'Wikipedia-logo.svg', 'Nuvola_apps_kmessedwords.png',
    'Status_iucn3.1_VU.svg', 'Star_empty.svg', 'Chess_rlt45.svg', 'Red_Pencil_Icon.png', 'Flag_of_Switzerland.svg',
    'Pfeil_unten.svg', 'Seal_of_California.svg', 'Nuvola_apps_ksim.png', 'Flag_of_Oklahoma_City,_Oklahoma.png',
    'Pfeil_rechts.svg', 'Gnome-mime-audio-openclipart.svg', 'Wikipedia-logo-v2.svg', 'The_Metropolitan_M_Stamp.PNG',
    'Chess_rdt45.svg', 'California_1.svg', 'USS_Lexington_Coral_Sea_early_morning.jpg', 'Dragon-149393.svg',
    'California_35.svg', 'Gnome-globe.svg', 'Flag_of_Monaco.svg', 'Wikiversity-logo-en.svg', 'US_101_(1961_cutout).svg',
    'Bandera_del_Primer_Imperio_Mexicano.svg', 'Kit_right_arm_Crusadersright16.png',
    'Pending-protection-shackle.svg', 'Gnome-speakernotes.svg', 'Aum_Om_red.svg', 'Sound-icon.svg', 'Portal-puzzle.svg',
    'Kit_left_arm_Crusadersleft16b.png', 'Royal_Standard_of_the_King_of_France.svg', 'Nuvola_apps_bookcase.svg',
    'Audio_a.svg', 'Flag_of_Japan_(1870-1999).svg', 'Kit_left_arm.svg', 'Symbol_template_class.svg',
    'Battle_of_Blenhiem_-_Situation_about_noon,_13_August_1704.gif', 'GM_headquarters_in_Detroit.JPG',
    'WPVG_icon_2016.svg', 'BS_Bismarck.png', 'Flag_of_Samoa.svg', 'Banner_of_the_Holy_Roman_Emperor_(after_1400).svg',
    'Flag_of_Hanover_1837-1866.svg', 'Flag_of_Great_Britain_(1707-1800).svg', 'Gold_medal_icon_(G_initial).svg',
    'Union_flag_1606_(Kings_Colors).svg', 'Kit_shorts_Crusadersshorts17.png', 'Flag_of_Cross_of_Burgundy.svg',
    'Symbol_list_class.svg', 'Wikibooks-logo.svg', 'Wiktionary-logo-en-v2.svg', 'Equador_physical_map.svg',
    'Flag_of_Canada_(Pantone).svg', 'Nuvola_apps_kalzium.svg', 'IRFU_flag.svg', 'Blank.png', 'Okapi2.jpg',
    'Extended-protection-shackle.svg', 'Bandera_de_España_1701-1748.svg', 'Flag_of_Bavaria_(lozengy).svg',
    'Kit_right_arm_Crusadersright16b.png', 'Asia_(orthographic_projection).svg', 'Industry5.svg',
    'Wikiversity-logo.svg', 'Skull_and_Crossbones.svg', 'Kit_socks_Crusaderssock17b.png', 'Kit_socks_long.svg',
    'Wikivoyage-Logo-v3-icon.svg', 'Chess_pdt45.svg', 'Pavillon_royal_de_la_France.svg', 'Motorsport_current_event.svg',
    'US-NationalParkService-ShadedLogo.svg', 'P_christianity.svg', 'Cheshire_Flag.svg', 'Book_collection.jpg',
    'Stylised_atom_with_three_Bohr_model_orbits_and_stylised_nucleus.svg', 'Wiktionary-logo-v2.svg',
    'Move-protection-shackle.svg', "Flag_of_the_People's_Republic_of_China.svg", 'Decrease_Positive.svg',
    'California_county_map_(San_Francisco_County_enlarged).svg', 'Flag_of_Russia.svg', '2hockeypucks.jpg',
    'USS_Lexington_under_attack_at_Coral_Sea.jpg', 'Edit-clear.svg', 'Sportcar_sergio_luiz_ara_01.svg',
    'Kit_body_Crusaderskit17.png', 'Chess_qlt45.svg', 'Star_full.svg', 'Flag_of_Argentina.svg',
    'War_Ensign_of_Germany_(1903–1919).svg', 'Wikiquote-logo.svg', 'Flag_of_Brazil.svg', 'Pfeil_oben.svg',
    'Silver_medal_icon_(S_initial).svg', 'A_coloured_voting_box.svg', 'National_Rail_logo.svg', 'P_history.svg',
    'Statenvlag.svg', 'Flag_of_Fiji.svg', 'England_relief_location_map.jpg', 'Sf-userbox.png',
    'Flag_of_France.svg', 'Arrow_Blue_Right_001.svg', 'Flag_of_the_United_States.svg', 'BelarusStub.svg',
    'Red_pog.svg', 'Increase2.svg', 'Silver_medal_icon.svg', 'Leningrad_bede.jpg', 'Tree_of_life.svg',
    'Flag_of_Tonga.svg', 'Flag_of_Mexico.svg', 'Four_Provinces_Flag.svg', '626Byzantium.svg', 'Cscr-featured.svg',
    'G13065_USS_Yorktown_Pearl_Harbor_May_1942.jpg', 'Flag_of_California.svg', 'Kit_socks_Crusaderssocks17.png',
    'Treecreepermap.png', 'Vampire_Smiley.png', 'California_82.svg', 'Chess_qdt45.svg', 'Flag_of_Japan_(1870–1999).svg',
    'Flag_of_Canada.svg', 'Bandera_de_España_1701-1760.svg', 'USS_Lexington_brennt.jpg', 'US_101_(CA).svg',
    'Arrow_Blue_Left_001.svg', 'Derafsh_Kaviani_flag_of_the_late_Sassanid_Empire.svg',
    'Large_explosion_aboard_USS_Lexington_(CV-2),_8_may_1942.jpg', 'LA_Skyline_Mountains2.jpg', 'White_flag_icon.svg',
    'Europe_orthographic_Caucasus_Urals_boundary_(with_borders).svg', 'Kit_left_arm_Crusadersleft16.png',
    'British_Empire_1897.jpg', '大洋.png', 'Decrease2.svg', 'SF_From_Marin_Highlands3.jpg', 'Flag_of_Ireland.svg',
    'Merchant_flag_of_Japan_(1870).svg', 'Flag_of_Sweden.svg', 'Skull_and_crossbones.svg', 'Folder_Hexagonal_Icon.svg',
    'Diocese_of_Winchester_arms.svg', 'Kit_body_Crusaderskit17b.png', 'Animation_disc.svg', 'Chess_nlt45.svg',
    'Flag_of_Belarus.svg', 'Star_half.svg', 'Om_symbol.svg', 'Simpsons_tv_icon.svg', 'Flag_of_Indonesia.svg',
    'Chess_klt45.svg', 'Chess_blt45.svg', 'Wind-turbine-icon.svg', 'Flag_of_the_United_States_(1848-1851).svg',
    'Flag_of_England.svg', "Saint_Patrick's_Saltire.svg", 'Semi-protection-shackle.svg', 'Global_thinking.svg',
    'Gnome-mime-sound-openclipart.svg', 'War_Ensign_of_Germany_1903-1918.svg', 'Wikinews-logo.svg',
    'Double-dagger-14-plain.png', 'Underground_no-text.svg', 'Kreuz-hugenotten.svg',
    'Mary_Wollstonecraft_Shelley_Rothwell.tif', 'Bluetank.png', 'Flag_of_the_Habsburg_Monarchy.svg'
]

class _MyHTMLParser(HTMLParser):
    _description = ""
    _tag_counter = 0
    
    def handle_starttag(self, tag, attrs):
        if self._tag_counter > 0:
            self._tag_counter += 1
        
        for attr in attrs:
            if attr == ('class', 'description'):
                self._tag_counter = 1
                

    def handle_endtag(self, tag):
        if self._tag_counter > 0:
            self._tag_counter -= 1

    def handle_data(self, data):
        if self._tag_counter > 0:
            self._description += data
        
    def get_description(self):
        return self._description
    

# onyshchak todo: move text cleaning to dataset preprocessing part 
# def _clean(wiki_text):
#     wikicode = mwp.parse(wiki_text)
#     return wikicode.strip_code()

def _get_translated_file_label(language_code):
    # to identify the correct translation, follow these steps:
    # 1) open some Wikipedia article in required language
    # 2) click on any image to get a full-window preview
    # 3) look-up on the url page in the browser. The required translation
    #   would be just after the last "/", such as in this example it will be "Archivo:"
    # https://es.wikipedia.org/wiki/A_Christmas_Carol#/media/Archivo:Charles_Dickens-A_Christmas_Carol-Cloth-First_Edition_1843.jpg
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

def _dump(path, data):
    with open(path, 'w', encoding='utf8') as outfile:
        json.dump(data, outfile, indent=2, ensure_ascii=False)
        
def _getJSON(path):
    with open(path) as json_file:
        return json.loads(json.load(json_file))

def _get_path(out_dir, create_if_not_exists):
    requests_path = Path(out_dir)
    if not requests_path.exists() and create_if_not_exists:
        requests_path.mkdir(parents=True)
      
    return requests_path

def _get_url(img_name, size=600):
    # onyshchak: img.oldest_file_info.url might have the same information
    url_prefix = "https://upload.wikimedia.org/wikipedia/commons/thumb/"
    md5 = hashlib.md5(img_name.encode('utf-8')).hexdigest()
    sep = "/"
    
    img_name = urllib.parse.quote(img_name)
    url = url_prefix + sep.join((md5[0], md5[:2], img_name)) + sep + str(size) + "px-" + img_name
    if url[-4:] != ".jpg" and url[-4:] != "jpeg":
        url += ".jpg"
        
    return url

def _get_description(img):
    parser = _MyHTMLParser()
    parser.feed(img.getImagePageHtml())
    return parser.get_description().replace("\n", "")

def _get_img_path(img, img_dir):
    img_name = img.title(as_filename=True, with_ns=False).replace("\"", "")
    img_name_valid = hashlib.md5(img_name.encode('utf-8')).hexdigest()  
    img_path = img_dir / (img_name_valid + ".jpg")
    
    img_path_orig = Path(str(img_path) + "_" + Path(img_name).suffix + ".ORIGINAL")
    # img_path_orig = Path(str(img_path) + "_" + img_name + ".ORIGINAL")
    # if len(str(img_path_orig).encode('utf-8')) >= 260:
    #     # pathlib doesn't support Win long path =(
    #     img_path_orig = Path(str(img_path) + "_" + Path(img_name).suffix + ".ORIGINAL")
        
    return img_name, img_path, img_path_orig

def _valid_img_type(img_name):
    valid_types = [
        '.tif', '.tiff', '.jpg', '.jpeg', '.jpe', '.jif,', '.jfif', '.jfi',  '.gif', '.png', '.svg'
    ]
    for t in valid_types:
        if img_name.lower().endswith(t):
            return True
    return False

def _single_img_download(img, img_dir, debug_info):
    img_name, img_path, img_path_orig = _get_img_path(img, img_dir)
    if not _valid_img_type(img_name):
        if img_path.exists():
            img_path.unlink()
                
        return (False, "")
    
    if img_path.exists():
        return (False, img_path.name)
    
    if img_path_orig.exists():
        return (False, img_path_orig.name)
    
    if debug_info: print('Downloading image', img_name)
    try:
        urlretrieve(_get_url(img_name), img_path)
        return (True, img_path.name) 
    except Exception as e:
        print(str(e))
        img.download(filename=img_path_orig, chunk_size=8*1024)
        return (True, img_path_orig.name)

def _remove_invalid_imgs(img_dir):
    files = [img_dir/f for f in listdir(img_dir) if isfile(join(img_dir, f))]
    for fpath in files:
        if stat(fpath).st_size == 0:
            print("Removing corrupted image", fpath)
            fpath.unlink()
    
def _remove_obsolete_imgs(img_dir, img_links):
    uptodate_imgs = [_get_img_path(img, img_dir) for img in img_links]
    img_names = (
        [x[1].name for x in uptodate_imgs if _valid_img_type(x[0])] +
        [x[2].name for x in uptodate_imgs if _valid_img_type(x[0])]
    )
    
    files = [img_dir/f for f in listdir(img_dir) if isfile(join(img_dir, f))]
    for fpath in files:
        fname = fpath.name
        if (fname not in img_names) and fname[-5:].lower() != ".json":
            print("Removing obsolete image", fpath)
            fpath.unlink()
    
    meta_path = img_dir/'meta.json'
    if not meta_path.exists():
        return
    
    meta = _getJSON(meta_path)
    uptodate_meta = [x for x in meta['img_meta'] if x['filename'] in img_names]
    if len(meta['img_meta']) != len(uptodate_meta):
        print("META", img_dir)
        meta_json = json.dumps({"img_meta": uptodate_meta})
        _dump(meta_path, meta_json)
        
def _is_meta_outdated(meta_path, img_links, params):
    if not meta_path.exists():
        return True

    if not params.invalidate_oudated_img_meta_cache:
        return False
    
    meta = _getJSON(meta_path)['img_meta']
    meta_titles = [x['title'] for x in meta]
    current_titles = [
        x.title(with_ns=False)
        for x in img_links if _valid_img_type(x.title(with_ns=False))
    ]
    
    res = sorted(meta_titles) != sorted(current_titles)
    if res and params.debug_info: print("OUTDATED META",  meta_path)
    return res
    

def _img_download(img_links, page_dir, params, tc, uc):
    if params.invalidate_img_cache:
        shutil.rmtree(page_dir/"img", ignore_errors=True)
        
    img_dir = _get_path(page_dir/"img", create_if_not_exists=True)
    meta_path = img_dir / 'meta.json'

    _remove_invalid_imgs(img_dir)
    if params.invalidate_img_meta_cache or params.invalidate_oudated_img_meta_cache:
        _remove_obsolete_imgs(img_dir, img_links)
    
    download_meta = (
        params.invalidate_img_meta_cache or
        _is_meta_outdated(meta_path, img_links, params)
    )

    if download_meta and params.debug_info: print("Updating image metadata")
    meta = []
    for img in img_links:
        downloaded, filename = _single_img_download(img, img_dir, params.debug_info)
        if downloaded: 
            tc += 1
            
        if download_meta and filename != "":
            meta.append({
                "filename": filename,
                "title": img.title(with_ns=False),
                "url": img.full_url(),
                'on_commons': not filename.endswith('.ORIGINAL'),
            })

            description = _get_description(img)
            if len(description) > 0:
                meta[-1]['description'] = description
          
    if download_meta:
        meta_json = json.dumps({"img_meta": meta})
        _dump(meta_path, meta_json)
    
    return (tc, uc)

# def _file_log(coll, filename):
#     with open(filename, 'w') as f:
#         for item in coll:
#             f.write("%s\n" % item)
            
def _validated_limit(limit, offset, list_len):
    res = limit if limit else list_len - offset
    return min(res, list_len - offset)

def _remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def _get_image_captions(page_url, language_code, debug_info):
    response = urllib.request.urlopen(page_url)
    page_html = response.read()
        
    res = []
    soup = BeautifulSoup(page_html, 'html.parser')
    for div in soup.findAll("div", {"class": "thumbcaption"}):
        offset = len('/wiki/')
        referenced_image = div.find("a", {"class": "internal"})
        if not referenced_image: 
            continue
            
        filename = unquote(referenced_image.get('href')[offset:])
        if not filename.startswith(_get_translated_file_label(language_code)):
            if debug_info: print('WARNING: Cannot parse url {}'.format(filename))
            continue
        
        res.append((filename, div.text))
    return res

def _parse_caption_with_js(driver, language_code, page_id, img_id, debug_info):
    caption = None
    if img_id in KNOWN_ICONS:
        if debug_info: print('Skipping known icon', img_id)
        return caption

    url = 'https://{}.wikipedia.org/wiki/{}#/media/{}{}'.format(
        language_code, page_id, _get_translated_file_label(language_code), img_id
    )
    if debug_info: print('Downloading captions for', url)
    driver.get(url)

    sleep_time = 1
    time.sleep(sleep_time) # reqired for JS to load content
    for k in range(5):
        try:
            # TODO: there is a bug when trying to parse noviewer thum. Driver returns caption from previous page
            # Currently not reproducible when invalidate_cache=False and caption already exists
            caption = driver.find_element_by_class_name("mw-mmv-title").text
            if caption == "":
                caption = None
                raise Exception
            else:
                break
        except:
            time.sleep(sleep_time) # reqired for JS to load content
            print("RETRY", k, " ||| ", img_id)
    
    # closing the tab so that we won't read it again if next page fails to load
    default_url = 'https://www.wikipedia.org/'
    driver.get(default_url)
    return caption
            
# Time-consuming but exhoustive fetching of image captions. On the other hand,
# fetch_meta_captions_fast is a fast alternative, although it misses around 20% of labels
def _query_img_captions_from_preview(
    filename,
    out_dir,
    offset=0,
    limit=None,
    language_code='en',
    invalidate_cache=False,
    debug_info=False
):
    site = pywikibot.Site(language_code)    
    pages = list(pagegenerators.TextfilePageGenerator(filename=filename, site=site))
    limit = _validated_limit(limit, offset, len(pages))
    
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    
    icons = set()
    for j in range(offset, offset + limit):
        p = pages[j]
        if p.pageid == 0:
            print("\nERROR: Cannot fetch the page " + p.title())
            continue
        
        page_dir = _get_path(out_dir + p.title(as_filename=True).rstrip('.'), create_if_not_exists=False)
        if not page_dir.exists():
            print('\nArticle "{}" is missing from expected path={}'.format(p.title(), page_dir))
            continue
            
        if debug_info: print('\n{}) {}'.format(j, page_dir))
        img_dir = _get_path(page_dir/"img", create_if_not_exists=False)
        meta_path = img_dir / 'meta.json'
        meta_arr = _getJSON(meta_path)['img_meta']
        
        page_id = p.title(as_filename=True).rstrip('.')
        for img in p.imagelinks():
            if not _valid_img_type(img.title(with_ns=False)):
                continue
                            
            img_id = img.title(as_filename=True, with_ns=False)
            file_label = _get_translated_file_label(language_code)
            res = [
                i for i, x in enumerate(meta_arr)
                if unquote(x['url']).split('/wiki/{}'.format(file_label))[-1] == img_id
            ]
            if len(res) != 1:
                if debug_info : print('WARNING: Meta for page {} is missing the image {}. Either was'\
                    ' removed intentionally or cache is outdated'.format(page_id, fileimg_idname))
                continue
            
            i = res[0]
            if 'caption' in meta_arr[i] and not invalidate_cache:
                if debug_info: print('Skipping cached caption', img_id) 
                continue
            
            caption = _parse_caption_with_js(
                driver, language_code, page_id, img_id, debug_info
            )

            if caption is None: icons.add(img_id)
            meta_arr[i].pop('caption', None)
            meta_arr[i]['is_icon'] = (caption is None)
            
            caption_match_description = (
                (not 'description' in meta_arr[i]) or
                (caption != _remove_prefix(meta_arr[i]['description'], "English: "))
            )
            
            if caption and caption_match_description:
                meta_arr[i]['caption'] = caption
            
        _dump(meta_path, json.dumps({"img_meta": meta_arr}))
            
    print(icons)
    driver.quit()

# Please check documentation for fetch_meta_captions for more details
# prerequisites
def _query_img_captions_from_article(
    filename,
    out_dir,
    offset=0,
    limit=None,
    language_code='en',
    invalidate_cache=False,
    debug_info=False
):
    site = pywikibot.Site(language_code)    
    pages = list(pagegenerators.TextfilePageGenerator(filename=filename, site=site))
    limit = _validated_limit(limit, offset, len(pages))
    
    for i in range(offset, offset + limit):
        p = pages[i]
        if p.pageid == 0:
            print("\nERROR: Cannot fetch the page " + p.title())
            continue
        
        page_dir = _get_path(out_dir + p.title(as_filename=True).rstrip('.'), create_if_not_exists=False)
        if not page_dir.exists():
            print('\nArticle "{}" is missing from expected path={}'.format(p.title(), page_dir))
            continue
    
        if debug_info: print(i, page_dir)        
        meta_path = join(page_dir, 'img', 'meta.json')
        meta_arr = _getJSON(meta_path)['img_meta']

        if invalidate_cache:
            for m in meta_arr:
                m.pop('caption', None)
        
        text_path = join(page_dir, 'text.json')
        article_url = _getJSON(text_path)['url']
        
        image_captions = _get_image_captions(article_url, language_code, debug_info)
        for filename, caption in image_captions:
            if not _valid_img_type(filename): continue
            
            res = [i for i, x in enumerate(meta_arr) if unquote(x['url']).split('/wiki/')[-1] == filename]
            if len(res) != 1:
                if debug_info : print('WARNING: Meta for page {} is missing the image {}. Either was'\
                    ' removed intentionally or cache is outdated'.format(page_dir, filename))
                continue
            
            i = res[0]
            meta_arr[i]['caption'] = caption
            meta_arr[i]['is_icon'] = False # preview only applies to not-icons
                
        _dump(meta_path, json.dumps({"img_meta": meta_arr}))


#########################################################################################################
# Public Interface
#########################################################################################################

@dataclass
class QueryParams:
    # specifies directory to download dataset. If it already contains part of dataset, that
    # part will be skipped unless you explicitly specify with parameters to invalidate the cache
    out_dir: str = '../data/'

    # if True, will print a lot of verbose information about the progress
    debug_info: bool = True

    # index of starting article from file to download
    offset: int = 0

    # limit of articles to download. If None, downloads from @offset to the end
    limit: Optional[int] = None

    # if True, will remove all cached images and their metadata
    invalidate_img_cache: bool = False 

    # if True, will redownload image metadata and all missing images. It will
    # skip already downloaded images and will also delete obsolete cached images
    invalidate_img_meta_cache: bool = False

    # if True, will check whether actual list of article images matched the cached one. If not, will
    # proceed with this particular meta.json as if @invalidate_img_meta_cache=True
    # Consecuently, has no affect when @invalidate_img_meta_cache=True already
    invalidate_oudated_img_meta_cache: bool = False

    # if True, will remove all cached text.json, i.e. textual content of the article
    invalidate_text_cache: bool = False

    # if True and any @invalidate_*_cache parameter is also True, will iterate over 
    # only downloaded articles from the @filename list specified and update them
    only_update_cached_pages: bool = False

    # code of Wikipedia language, articles of which specified in @filename list. All articles
    # in @filename should be from a single wikipedia.
    language_code: str = 'en'
        
def query_size(filename: str):
    site = pywikibot.Site()
    pages = list(pagegenerators.TextfilePageGenerator(filename=filename, site=site))
    
    return len(pages)

def query(filename: str, params: QueryParams) -> None:   
    site = pywikibot.Site(params.language_code)    
    pages = list(pagegenerators.TextfilePageGenerator(filename=filename, site=site))
    limit = _validated_limit(params.limit, params.offset, len(pages))
    
    print('Downloading... offset={}, limit={}'.format(params.offset, limit))
    tc, uc = 0, 0
    for i in range(params.offset, params.offset + limit):
        p = pages[i]
        if p.pageid == 0:
            print("\nERROR: Cannot fetch the page " + p.title())
            continue
            
        # onyshchak: create_if_not_exists - switch to enrich only existing data
        page_dir = _get_path(
            out_dir = params.out_dir + p.title(as_filename=True).rstrip('.'),
            create_if_not_exists = not params.only_update_cached_pages
        )
        
        if not page_dir.exists():
            continue 
        
        if params.debug_info: print('\n{}) {}'.format(i, page_dir))  
        should_download_article = lambda path: (
            not path.exists() or
            stat(path).st_size == 0 or
            params.invalidate_text_cache
        )
        
        text_path = page_dir / 'text.json'
        if should_download_article(text_path):
            if params.debug_info: print("Downloading text.json")
            page_json = json.dumps({
                "title": p.title(),
                "id": p.pageid,
                "url": p.full_url(),
                "wikitext": p.text,
                "html": urllib.request.urlopen(p.full_url()).read().decode("utf-8"),
            })
             
            _dump(text_path, page_json)
            
        # downloading page images
        tc, uc = _img_download(p.imagelinks(), page_dir, params, tc, uc)           
            
    print('\nDownloaded {} images, where {} of them unavailable from commons'.format(tc, uc))

# TODO: exreact features from all ORIGINAL files
# Downloads or updates image descriptions in cached dataset. It is used internally in query function and
# was also extracted into standalone function just for convenience when you want to update description
# without redownloading images
def query_img_descriptions(filename, out_dir, offset=0, limit=None, language_code='en'):
    site = pywikibot.Site(language_code)    
    pages = list(pagegenerators.TextfilePageGenerator(filename=filename, site=site))
    limit = _validated_limit(limit, offset, len(pages))
    
    for i in range(offset, offset + limit):
        p = pages[i]
        if p.pageid == 0:
            print("\nERROR: Cannot fetch the page " + p.title())
            continue
        
        page_dir = _get_path(out_dir + p.title(as_filename=True).rstrip('.'), create_if_not_exists=False)
        if not page_dir.exists():
            print('\nArticle "{}" is missing from expected path={}'.format(p.title(), page_dir))
            continue
            
        print(i, p.title())
        img_dir = _get_path(page_dir/"img", create_if_not_exists=False)
        meta_path = img_dir / 'meta.json'
        meta = _getJSON(meta_path)
        
        updated = False
        for img in p.imagelinks():
            if not _valid_img_type(img.title(with_ns=False)):
                continue
            
            i = next(i for i,x in enumerate(meta['img_meta']) if x['title'] == img.title(with_ns=False))
            updated_description = _get_description(img)
            if updated_description != meta['img_meta'][i]['description']:
                updated = True
                meta['img_meta'][i]['description'] = _get_description(img)
                print("DESCRIPTION", img_dir/meta['img_meta'][i]['filename'])
            
        if updated:
            meta_json = json.dumps(meta)
            _dump(meta_path, meta_json)

# Queries HTML-pages of articles and enriches dataset with parsed image captions.
# TODO: handle parsing of "noviewer thumb" class images as well. Mostly for icons, not relevant
def query_img_captions(
    filename, out_dir, offset=0, limit=None, language_code='en', invalidate_cache=False, debug_info=False
):
    if debug_info: print("Querying available captions with fast approach\n")
    _query_img_captions_from_article(
        filename=filename,
        out_dir=out_dir,
        offset=offset,
        limit=limit,
        language_code=language_code,
        invalidate_cache=invalidate_cache,
        debug_info=debug_info
    )

    if debug_info: print("\nQuerying remaining unparsed caption with time-consuming approach\n")
    _query_img_captions_from_preview(
        filename=filename,
        out_dir=out_dir,
        offset=offset,
        limit=limit,
        language_code=language_code,
        # should always be False, since we already invalidated the cache in _query_img_captions_from_article
        invalidate_cache=False,
        debug_info=debug_info
    )
