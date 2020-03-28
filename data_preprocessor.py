import pandas as pd
import numpy as np
import string
import json
import shutil
import os

from pathlib import Path
from os import listdir, mkdir
from os.path import isfile, isdir, join, exists, abspath
from keras.preprocessing import image
from keras.applications.resnet import ResNet152, preprocess_input
from sklearn.model_selection import train_test_split

def _getJSON(path):
    with open(path) as json_file:
        return json.loads(json.load(json_file))
    
def _dump(path, data):
    with open(path, 'w', encoding='utf8') as outfile:
        json.dump(data, outfile, indent=2, ensure_ascii=False)

def _global_max_pool_1D(tensor):
    _,_,_,size = tensor.shape
    return [tensor[:,:,:,i].max() for i in range(size)]

def _get_image_features(model, img_path):
    img = image.load_img(img_path, target_size=None)

    img_data = image.img_to_array(img)
    img_data = np.expand_dims(img_data, axis=0)
    img_data = preprocess_input(img_data)

    feature_tensor = model.predict(img_data)
    get_img_id = lambda p: p.split('/')[-1].split('.')[0]
    return {
        "id": get_img_id(img_path),
        "features": _global_max_pool_1D(feature_tensor),
    }

################################################################################
# Public Interface
################################################################################

def generate_visual_features(
    data_path, offset=0, limit=None, model=None, debug_info=False
):
    article_paths = [
        join(data_path, f) 
        for f in listdir(data_path) if isdir(join(data_path, f))
    ]
    
    limit = limit if limit else len(article_paths) - offset
    limit = min(limit, len(article_paths) - offset)
    model = model if model else ResNet152(weights='imagenet', include_top=False) 
    
    for i in range(offset, offset + limit):
        path = article_paths[i]
        if debug_info: print(i, path)
    
        meta_path = join(path, 'img/', 'meta.json')
        meta_arr = _getJSON(meta_path)['img_meta']
        for meta in meta_arr:
            if 'features' in meta: continue
            if meta['filename'][-4:].lower() != ".jpg": continue
                
            img_path =  join(path, 'img/', meta['filename'])
            try:
                features = _get_image_features(model, img_path)['features']
                meta['features'] = [str(f) for f in features]
            except Exception as e:
                print("ERROR: exception for image", img_path, '|||', str(e))
                continue
                
        _dump(meta_path, json.dumps({"img_meta": meta_arr}))
        
def filter_img_metadata(
    data_path, predicate, field_to_remove, offset=0, limit=None, debug_info=False
):
    article_paths = [
        join(data_path, f)
        for f in listdir(data_path) if isdir(join(data_path, f))
    ]

    limit = limit if limit else len(article_paths) - offset
    limit = min(limit, len(article_paths) - offset)
    
    for i in range(offset, offset + limit):
        path = article_paths[i]
        if debug_info: print(i, path)
    
        meta_path = join(path, 'img/', 'meta.json')
        meta_arr = _getJSON(meta_path)['img_meta']
        
        meta_arr_filtered = [x for x in meta_arr if predicate(x)]
        for x in meta_arr_filtered:
            # useless fields since now it always the same
            x.pop(field_to_remove, None)
                
        _dump(meta_path, json.dumps({"img_meta": meta_arr_filtered}))

