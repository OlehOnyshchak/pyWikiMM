import pandas as pd
import numpy as np
import string
import json
import shutil
import re
import os

from bs4 import BeautifulSoup
from bs4.element import Tag
from pathlib import Path
from os import listdir, mkdir
from os.path import isfile, isdir, join, exists, abspath
from keras.preprocessing import image
from keras.applications.resnet import ResNet152, preprocess_input
from sklearn.model_selection import train_test_split
from redditscore.tokenizer import CrazyTokenizer
from urllib.parse import unquote
from abc import ABC, abstractmethod
from typing import Union, List, Dict, Tuple, Sequence, Callable, Any
from utils import (
    _getJSON,
    _dump,
    _get_translated_file_label,
    _valid_img_type,
    _validated_limit,
    JSONSerializableType,
)

def _is_valid_img_src(img_src: str, lang: str) -> bool:
    special_img = '//{}.wikipedia.org/wiki/Special:CentralAutoLogin/start?type=1x1'.format(lang)
    # TODO: check if we can or need to work out with maps
    return (
        img_src != special_img
        and not img_src.startswith('https://maps.wikimedia.org')
        and not img_src.startswith('https://wikimedia.org/api/rest_v1/media/math/render/svg/')
        and not img_src.startswith('/api/rest_v1/page/graph/')
        and not img_src.startswith('/w/extensions/')
        and not img_src.startswith('//upload.wikimedia.org/score/')
    )

def _get_img_name(img_src: str, lang: str) -> str:
    COMMONS_IMG_SRC = '//upload.wikimedia.org/wikipedia/commons/thumb/'
    COMMONS_NO_THUMB_IMG_SRC = '//upload.wikimedia.org/wikipedia/commons/'
    WIKI_IMG_SRC = '//upload.wikimedia.org/wikipedia/{}/thumb/'.format(lang)
    WIKI_NO_THUMB_IMG_SRC = '//upload.wikimedia.org/wikipedia/{}/'.format(lang)
    STATIC_IMG_SRC = '/static/images/'
    
    hash_len = len('e/e7/')
    def _get_img_name_common(offset):
        img_name = img_src[offset:]
        if '/'in img_name:
            img_name = img_name[:img_name.index('/')]
        return img_name
    
    offset = None
    if img_src.startswith(COMMONS_IMG_SRC):
        offset = len(COMMONS_IMG_SRC) + hash_len
    elif img_src.startswith(COMMONS_NO_THUMB_IMG_SRC):
        offset = len(COMMONS_NO_THUMB_IMG_SRC) + hash_len
    elif img_src.startswith(WIKI_IMG_SRC):
        offset = len(WIKI_IMG_SRC) + hash_len
    elif img_src.startswith(WIKI_NO_THUMB_IMG_SRC):
        offset = len(WIKI_NO_THUMB_IMG_SRC) + hash_len
    elif img_src.startswith(STATIC_IMG_SRC):
        offset = len(STATIC_IMG_SRC)
    else:
        raise Exception("ERROR: unknown img_src format:", img_src)
        
    return unquote(_get_img_name_common(offset))

def _get_heading_text(tag_element: Tag) -> str:
    text = tag_element.text.strip()
    # TODO: check if that could be done more reliable and whether nested brackets
    # are possible
    if text[-1] == ']' and '[' in text:
        text = text[:text.rfind('[')]
    return text

def _get_headings(tag_element: Tag) -> List[str]:
    res = []
    arr = [
        (x.name, _get_heading_text(x))
        for x in tag_element.find_all_previous(re.compile('h[1-6]'))
    ]
    tagname_arr = [x for x, _ in arr]
    for i in range(1, 7):
        tag = 'h{}'.format(i)
        if tag not in tagname_arr:
            continue
    
        parent_index = tagname_arr.index(tag)
        res.append(arr[parent_index][1])
        tagname_arr = tagname_arr[:parent_index]
        
    return res

def _get_image_headings(page_html: str, lang: str) -> Dict[str, List[str]]:
    soup = BeautifulSoup(page_html, 'html.parser')
    
    res = {}
    for x in soup.findAll("img"):
        img_src = x.get('src')
        if not _is_valid_img_src(img_src, lang):
            continue
        
        img_name = _get_translated_file_label(lang) + _get_img_name(img_src, lang)
        res[img_name] = _get_headings(x)
    
    return res

def _parse_img_headings(
    page_dir: str, invalidate_cache: bool, language_code: str
) -> None:
    meta_path = join(page_dir, 'img', 'meta.json')
    meta_arr = _getJSON(meta_path)['img_meta']

    if invalidate_cache:
        for m in meta_arr:
            m.pop('headings', None)
    
    text_path = join(page_dir, 'text.json')
    page_html = _getJSON(text_path)['html']
    
    image_headings = _get_image_headings(page_html, language_code)
    for filename, headings in image_headings.items():
        if not _valid_img_type(filename): continue
        if len(headings) == 0: continue
        
        res = [
            i for i, x in enumerate(meta_arr)
            if unquote(x['url']).split('/wiki/')[-1] == filename
        ]

        if len(res) != 1: continue
        i = res[0]

        # TODO: not update when invalidate_cache=False even though we already queried
        meta_arr[i]['headings'] = headings
            
    _dump(meta_path, {"img_meta": meta_arr})

################################################################################
# Public Interface
################################################################################

class IMapper(ABC):
    @abstractmethod
    def map(self, img_path: str) -> JSONSerializableType:
        ...

class ResNet152Mapper(IMapper):
    def __init__(self):
        self.model = ResNet152(weights='imagenet', include_top=False)

    def map(self, img_path: str) -> JSONSerializableType:
        img = image.load_img(img_path, target_size=None)

        img_data = image.img_to_array(img)
        img_data = np.expand_dims(img_data, axis=0)
        img_data = preprocess_input(img_data)

        feature_tensor = self.model.predict(img_data)
        features = ResNet152Mapper._global_max_pool_1D(feature_tensor)
        return features

    @staticmethod
    def _global_max_pool_1D(tensor: np.ndarray) -> List[float]:
        _,_,_,size = tensor.shape
        return [tensor[:,:,:,i].max() for i in range(size)]

def generate_visual_features(
    data_path: str,
    offset: int = 0,
    limit: int = None,
    mapper: IMapper = None,
    invalidate_cache: bool = False,
    debug_info: bool = False,
) -> None:
    article_paths = [
        join(data_path, f) 
        for f in listdir(data_path) if isdir(join(data_path, f))
    ]
    
    valid_limit = _validated_limit(limit, offset, len(article_paths))
    mapper = mapper if mapper else ResNet152Mapper() 
    
    for i in range(offset, offset + valid_limit):
        path = article_paths[i]
        if debug_info: print(i, path)
    
        meta_path = join(path, 'img/', 'meta.json')
        meta_arr = _getJSON(meta_path)['img_meta']
        for meta in meta_arr:
            if 'features' in meta and not invalidate_cache: 
                continue
                
            img_path =  join(path, 'img/', meta['filename'])
            try:
                meta['features'] = mapper.map(img_path)
            except Exception as e:
                print("ERROR: exception for image", img_path, '|||', str(e))
                continue
                
        _dump(meta_path, {"img_meta": meta_arr})
        
def filter_img_metadata(
    data_path: str,
    predicate: Callable[[Dict[str, Any]], bool],
    field_to_remove: str,
    offset: int = 0,
    limit: int = None,
    debug_info: bool = False,
) -> None:
    article_paths = [
        join(data_path, f)
        for f in listdir(data_path) if isdir(join(data_path, f))
    ]

    valid_limit = _validated_limit(limit, offset, len(article_paths))
    for i in range(offset, offset + valid_limit):
        path = article_paths[i]
        if debug_info: print(i, path)
    
        meta_path = join(path, 'img/', 'meta.json')
        meta_arr = _getJSON(meta_path)['img_meta']
        
        meta_arr_filtered = [x for x in meta_arr if predicate(x)]
        for x in meta_arr_filtered:
            # useless fields since now it always the same
            x.pop(field_to_remove, None)
                
        _dump(meta_path, {"img_meta": meta_arr_filtered})

def tokenize_image_titles(
    data_path: str,
    offset: int = 0,
    limit: int = None,
    invalidate_cache: bool = False,
    debug_info: bool = False,
) -> None:
    article_paths = [
        join(data_path, f) 
        for f in listdir(data_path) if isdir(join(data_path, f))
    ]
    
    valid_limit = _validated_limit(limit, offset, len(article_paths))
    tokenizer = CrazyTokenizer(hashtags='split')
    mapper = str.maketrans({x: '' for x in string.punctuation})
    regex = re.compile(r'(\d+)')

    for i in range(offset, offset + valid_limit):
        path = article_paths[i]
        if debug_info: print(i, path)
    
        meta_path = join(path, 'img/', 'meta.json')
        meta_arr = _getJSON(meta_path)['img_meta']
        for meta in meta_arr:
            if 'parsed_title' in meta and not invalidate_cache:
                continue
                
            filename = os.path.splitext(meta['title'])[0]
            sentence = filename.translate(mapper)
            sentence = regex.sub(r' \g<1> ', sentence)

            tokens = []
            for word in sentence.split():
                tokens += (
                    tokenizer.tokenize("#" + word) 
                    if not word.isdigit() 
                    else [word]
                )
            
            meta['parsed_title'] = " ".join(tokens)
                
        _dump(meta_path, {"img_meta": meta_arr})


# Parses image headings from the article. That is, updates @headings field of
# image metadata, which is a list containing all available headings from h1 to h6
def parse_image_headings(
    data_path: str,
    offset: int = 0,
    limit: int = None,
    invalidate_cache: bool = False,
    debug_info: bool = False,
    language_code: str = 'en',
) -> None:
    article_paths = [
        join(data_path, f) 
        for f in listdir(data_path) if isdir(join(data_path, f))
    ]
    
    valid_limit = _validated_limit(limit, offset, len(article_paths))
    for i in range(offset, offset + valid_limit):
        path = article_paths[i]
        if debug_info: print(i, path)
    
        _parse_img_headings(path, invalidate_cache, language_code)
