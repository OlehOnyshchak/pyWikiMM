# from __future__ import annotations  # optional, uncomment if py.version >= 3.7
import pywikibot
import json
import hashlib
import urllib
import re
import shutil
import time
import urllib.request

from pathlib import Path
from pywikibot import pagegenerators, Page
from pywikibot.data.api import PageGenerator
from urllib.request import urlretrieve
from html.parser import HTMLParser
from html.entities import name2codepoint
from os import listdir, stat
from os.path import isfile, join, basename
from dataclasses import dataclass
from typing import Optional
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.webdriver import WebDriver
from urllib.parse import unquote
from bs4 import BeautifulSoup
from typing import Set, Optional, List, Tuple
from pywikimm.utils import (
    _getJSON,
    _dump,
    _get_translated_file_label,
    _valid_img_type,
    _validated_limit,
    _KNOWN_ICONS_PATH,
    _KNOWN_ICONS,
)

# TODO: replace with beautifulsoup
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

def _get_path(out_dir: Path, create_if_not_exists: bool) -> Path:
    requests_path = Path(out_dir)
    if not requests_path.exists() and create_if_not_exists:
        requests_path.mkdir(parents=True)
      
    return requests_path

def _get_url(img_name: str, size: int = 600) -> str:
    # TODO: img.oldest_file_info.url might have the same information
    url_prefix = "https://upload.wikimedia.org/wikipedia/commons/thumb/"
    md5 = hashlib.md5(img_name.encode('utf-8')).hexdigest()
    sep = "/"
    
    img_name = urllib.parse.quote(img_name)
    url = url_prefix + sep.join((md5[0], md5[:2], img_name)) + sep + str(size) + "px-" + img_name
    if url[-4:] != ".jpg" and url[-4:] != "jpeg":
        url += ".jpg"
        
    return url

def _get_description(img: Page) -> str:
    parser = _MyHTMLParser()
    parser.feed(img.getImagePageHtml())
    return parser.get_description().replace("\n", "")

def _get_img_path(img: Page, img_dir: Path) -> Tuple[str, Path, Path]:
    img_name = unquote(img.title(with_ns=False, as_url=True))
    img_name_valid = hashlib.md5(img_name.encode('utf-8')).hexdigest()  
    img_path = img_dir / (img_name_valid + ".jpg")
    img_path_orig = Path(str(img_path) + "_" + Path(img_name).suffix + ".ORIGINAL")    
        
    return img_name, img_path, img_path_orig

def _single_img_download(
    img: Page, img_dir: Path, params: "QueryParams"
) -> Tuple[bool, str]:
    img_name, img_path, img_path_orig = _get_img_path(img, img_dir)
    if not _valid_img_type(img_name, params.early_icons_removal):
        if img_path.exists():
            img_path.unlink()
                
        return (False, "")
    
    if img_path.exists():
        return (False, img_path.name)
    
    if img_path_orig.exists():
        return (False, img_path_orig.name)
    
    if params.debug_info: print('Downloading image', img_name)
    try:
        urlretrieve(_get_url(img_name, params.img_width), img_path)
        return (True, img_path.name) 
    except Exception as e:
        print(str(e))
        img.download(filename=img_path_orig, chunk_size=8*1024)
        return (True, img_path_orig.name)

def _remove_invalid_imgs(img_dir: Path) -> None:
    files = [img_dir/f for f in listdir(img_dir) if isfile(join(img_dir, f))]
    for fpath in files:
        if stat(fpath).st_size == 0:
            print("Removing corrupted image", fpath)
            fpath.unlink()
    
def _remove_obsolete_imgs(
    img_dir: Path, img_links: PageGenerator, params: "QueryParams"
) -> None:
    uptodate_imgs = [_get_img_path(img, img_dir) for img in img_links]
    icon_removal = params.early_icons_removal
    img_names = (
        [x[1].name for x in uptodate_imgs if _valid_img_type(x[0], icon_removal)] +
        [x[2].name for x in uptodate_imgs if _valid_img_type(x[0], icon_removal)]
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
        _dump(meta_path, {"img_meta": uptodate_meta})
        
def _is_meta_outdated(
    meta_path: Path, img_links: PageGenerator, params: "QueryParams"
) -> bool:
    if not meta_path.exists():
        return True

    if not params.invalidate_cache.oudated_img_meta_cache:
        return False
    
    meta = _getJSON(meta_path)['img_meta']
    meta_titles = [x['title'] for x in meta]
    current_titles = [
        x.title(with_ns=False)
        for x in img_links
        if _valid_img_type(x.title(with_ns=False), params.early_icons_removal)
    ]
    
    res = sorted(meta_titles) != sorted(current_titles)
    if res and params.debug_info: print("OUTDATED META", meta_path)
    return res
    

def _img_download(
    img_links: PageGenerator,
    page_dir: Path,
    params: "QueryParams",
    tc: int,
    uc: int
) -> Tuple[int, int]:
    if params.invalidate_cache.img_cache:
        shutil.rmtree(page_dir/"img", ignore_errors=True)
        
    img_dir = _get_path(page_dir/"img", create_if_not_exists=True)
    meta_path = img_dir / 'meta.json'

    _remove_invalid_imgs(img_dir)
    if params.invalidate_cache.img_meta_cache or params.invalidate_cache.oudated_img_meta_cache:
        _remove_obsolete_imgs(img_dir, img_links, params)
    
    download_meta = (
        params.invalidate_cache.img_meta_cache or
        _is_meta_outdated(meta_path, img_links, params)
    )

    if download_meta and params.debug_info: print("Updating image metadata")
    meta = []
    for img in img_links:
        downloaded, filename = _single_img_download(img, img_dir, params)
        if downloaded: 
            tc += 1
            
        if download_meta and filename != "":
            meta.append({
                "filename": filename,
                "title": img.title(with_ns=False),
                "url": img.full_url(),
                'on_commons': not filename.endswith('.ORIGINAL'),
            })

            if params.fill_property.img_description:
                description = _get_description(img)
                if len(description) > 0:
                    meta[-1]['description'] = description
          
    if download_meta:
        _dump(meta_path, {"img_meta": meta})
    
    return (tc, uc)

def _remove_prefix(text: str, prefix: str) -> str:
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

def _get_image_captions(
    page_html: str, language_code: str, debug_info: bool
) -> List[Tuple[str, str]]:
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

def _parse_caption_with_js(
    driver: WebDriver,
    language_code: str,
    page_id: str,
    img_id: str,
    icons: Set[str],
    debug_info: bool
) -> Optional[str]:
    caption = None
    if img_id in _KNOWN_ICONS or img_id in icons:
        if debug_info: print('Skipping known icon', img_id)
        return caption

    url = 'https://{}.wikipedia.org/wiki/{}#/media/{}{}'.format(
        language_code, page_id, _get_translated_file_label(language_code), img_id
    )
    if debug_info: print('Downloading captions for', url)
    driver.get(url)

    sleep_time = 1
    retry_count = 2
    time.sleep(sleep_time) # reqired for JS to load content
    for k in range(retry_count):
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

def _query_img_captions_from_article(
    page_dir: Path,
    invalidate_cache: bool = False,
    language_code: str = 'en',
    debug_info: bool = False,
) -> None:
    meta_path = join(page_dir, 'img', 'meta.json')
    meta_arr = _getJSON(meta_path)['img_meta']

    if invalidate_cache:
        for m in meta_arr:
            m.pop('caption', None)
            m.pop('is_icon', None)
    
    text_path = join(page_dir, 'text.json')
    page_html = _getJSON(text_path)['html']
    
    image_captions = _get_image_captions(page_html, language_code, debug_info)
    for filename, caption in image_captions:
        if not _valid_img_type(filename): continue
        
        res = [i for i, x in enumerate(meta_arr) if unquote(x['url']).split('/wiki/')[-1] == filename]
        if len(res) != 1:
            if debug_info : print('WARNING: Meta for page {} is missing the image {}. Either was'\
                ' removed intentionally or cache is outdated'.format(page_dir, filename))
            continue
        
        i = res[0]
        caption_match_description = (
            ('description' not in meta_arr[i]) or
            (caption != _remove_prefix(meta_arr[i]['description'], "English: "))
        )

        if 'caption' not in meta_arr[i] and caption_match_description:
            meta_arr[i]['caption'] = caption
            meta_arr[i]['is_icon'] = False # preview only applies to not-icons
            
    _dump(meta_path, {"img_meta": meta_arr})

# Time-consuming but exhoustive fetching of image captions. On the other hand,
# fetch_meta_captions_fast is a fast alternative, although it misses around 20% of labels
def _query_img_captions_from_preview(
    page_dir: Path,
    driver: WebDriver,
    icons: Set[str],
    language_code: str = 'en',
    debug_info: bool = False,
) -> None:
    img_dir = _get_path(page_dir/"img", create_if_not_exists=False)
    meta_path = img_dir / 'meta.json'
    meta_arr = _getJSON(meta_path)['img_meta']
        
    page_id = basename(page_dir)
    if page_id == '':
        page_id = basename(str(page_dir)[:-1])

    for i, meta in enumerate(meta_arr):
        img_title = meta['title']
        if not _valid_img_type(img_title):
            continue

        file_label = _get_translated_file_label(language_code)
        # TODO: here we extract img_id without language-specific File: prefix
        # and later on we add it again to build a URL. Check whether we could
        # work WITH that language-specific part and thus avoid translations
        img_id = unquote(meta['url']).split('/wiki/{}'.format(file_label))[-1]
            
        if 'caption' in meta_arr[i]:
            if debug_info: print('Skipping cached caption', img_id) 
            continue

        if 'is_icon' in meta_arr[i] and meta_arr[i]['is_icon']:
            if debug_info: print('Skipping known icon', img_id) 
            continue
            
        caption = _parse_caption_with_js(
            driver, language_code, page_id, img_id, icons, debug_info
        )

        if caption is None: icons.add(img_id)
        meta_arr[i].pop('caption', None)
        meta_arr[i]['is_icon'] = (caption is None)
            
        caption_match_description = (
            ('description' not in meta_arr[i]) or
            (caption != _remove_prefix(meta_arr[i]['description'], "English: "))
        )
            
        if caption and caption_match_description:
            meta_arr[i]['caption'] = caption
            
    _dump(meta_path, {"img_meta": meta_arr})

# This function is firstly trying to parse as many captions as possible with 
# a fast but unreliable approach. After that, it gathers all remaining captions
# with a time-consuming method, which is to download HTML preview-pages for each
# image in the article. Furthermore, it's dynamically generated content by
# javascript. Thus we need to execute that generating code internally when
# loading the page. Also generates 'is_icon' property for each field depending
# whether image has a preview. Also, when caption matches description, we will
# not record caption
def _query_img_captions(
    page_dir: Path,
    driver: WebDriver,
    icons: Set[str],
    language_code: str = 'en',
    invalidate_cache: bool = False,
    debug_info: bool = False,
) -> None:
    if debug_info:
        print("\nQuerying available captions with fast approach")

    _query_img_captions_from_article(
        page_dir=page_dir,
        language_code=language_code,
        invalidate_cache=invalidate_cache,
        debug_info=debug_info
    )

    if debug_info:
        print("\nQuerying remaining unparsed captions with time-consuming approach\n")

    _query_img_captions_from_preview(
        page_dir=page_dir,
        driver=driver,
        icons=icons,
        language_code=language_code,
        debug_info=debug_info
    )



################################################################################
# Public Interface
################################################################################

@dataclass
class FillPropertyParams:
    # if False, will not download meta.json['captions']. This is the most 
    # time-consuming operation in a script, so you might need to consider
    # whether to include it. Also note, that meta.json['is_icon'] is its derived
    # property, so it will only be present if you fill meta.json['captions']
    img_caption: bool = True

    # if False, will not download meta.json['description']
    img_description: bool = True

    # if False, will not download text.json['wikitext']
    text_wikitext: bool = True

    # if False, will not download text.json['html']
    text_html: bool = True

@dataclass
class InvalidateCacheParams:
    # if True, will remove all cached images and their metadata
    img_cache: bool = False 

    # if True, will redownload image metadata and all missing images. It will
    # skip already downloaded images and will also delete obsolete cached images
    img_meta_cache: bool = False

    # if True, will check whether actual list of article images matched the
    # cached one. If not, will proceed with this particular meta.json as if
    # @invalidate_img_meta_cache=True. Consecuently, has no affect when 
    # @invalidate_img_meta_cache=True already
    oudated_img_meta_cache: bool = False

    # if True, will remove all cached image captions, which are parsed from
    # article content
    caption_cache: bool = False

    # if True, will remove all cached text.json, i.e. textual content of
    # the article
    text_cache: bool = False

@dataclass
class QueryParams:
    # specifies directory to download dataset. If it already contains part of
    # a dataset, that part will be skipped unless you explicitly specify with
    # parameters to invalidate the cache
    out_dir: str = '../data/'

    # if True, will print a lot of verbose information about the progress
    debug_info: bool = True

    # index of starting article from file to download
    offset: int = 0

    # limit of articles to download. If None, downloads from @offset to the end
    limit: Optional[int] = None

    # set of paramaters to invalidate different kind of cached data.
    # Please see the definition above for specific documentation
    invalidate_cache: InvalidateCacheParams = InvalidateCacheParams()

    # if True and any of @invalidate_cache parameter is also True, will iterate 
    # over only downloaded articles from the @filename list specified and
    # update them
    only_update_cached_pages: bool = False

    # set of parameters to configure what data to download. Please see the
    # FillPropertyParams definition above for more details
    fill_property : FillPropertyParams = FillPropertyParams()

    # code of Wikipedia language, articles of which specified in @filename list.
    # All articles in @filename should be from a single wikipedia.
    language_code: str = 'en'

    # every image will be downloaded with specified width, while height will be
    # automatically calculated for each image to preserve the original
    # height/width ratio
    img_width: int = 600

    # if True, will optimise the collection process to not even download known
    # icons. Remove this flag if you want to get them
    early_icons_removal: bool = True

# queries wikipedia articles from the list specified by a @filename path. All
# data collection details can be configured via @params.
# @filename should be a path of a file with article ids specified one per line.
# By article id here we mean last part of its URL. That is, for the article with
# URL = https://en.wikipedia.org/wiki/The_Relapse on English Wikipedia, the id 
# would be "The_Relapse". Please note, that all article ids you specified in a 
# file should be from the same Wikipedia, i.e. either all English or all Ukrainian.
def query(filename: str, params: QueryParams) -> None:   
    site = pywikibot.Site(code=params.language_code, fam='wikipedia', user='pywikimm')    
    pages = list(pagegenerators.TextfilePageGenerator(filename=filename, site=site))
    limit = _validated_limit(params.limit, params.offset, len(pages))

    icons: Set[str] = set()

    # TODO: don't execute driver when fill_captions=Flase
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    
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
            params.invalidate_cache.text_cache
        )
        
        text_path = page_dir / 'text.json'
        if should_download_article(text_path):
            if params.debug_info: print("Downloading text.json")
            page_json = {
                "title": p.title(),
                "id": p.pageid,
                "url": p.full_url(),
            }

            if params.fill_property.text_wikitext:
                page_json["wikitext"] = p.text

            if params.fill_property.text_html:
                response = urllib.request.urlopen(p.full_url())
                page_json["html"] = response.read().decode("utf-8")
             
            _dump(text_path, page_json)
            
        # downloading page images
        tc, uc = _img_download(p.imagelinks(), page_dir, params, tc, uc)

        if params.fill_property.img_caption:
            _query_img_captions(
                page_dir=page_dir,
                driver=driver,
                icons=icons,
                language_code=params.language_code,
                invalidate_cache=params.invalidate_cache.caption_cache,
                debug_info=params.debug_info,
            )
            
    print('\nDownloaded {} images, where {} of them unavailable from commons'.format(tc, uc))
    driver.quit()

    icons_json = _getJSON(_KNOWN_ICONS_PATH)
    updated_icons = icons.union(icons_json['known_icons'])
    _dump(_KNOWN_ICONS_PATH, {"known_icons": list(updated_icons)})
