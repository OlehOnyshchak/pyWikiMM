#!/usr/bin/env python3
from pywikimm import reader
from pywikimm import preprocessor

################################################################################
## Please refer to data_collection_demo.ipynb for documentation
################################################################################

# TODO: change the filepath to your input file, if needed
filename = 'input.txt'
out_dir = 'data/'

invalidate_headings_cache = False
invalidate_parsed_titles_cache = False
invalidate_visual_features_cache = False

query_params = reader.QueryParams(
    out_dir = out_dir,
    debug_info = True,
    offset = 0,
    limit = 5,
    invalidate_cache = reader.InvalidateCacheParams(
        img_cache = False,
        text_cache = False,
        caption_cache = False,
        img_meta_cache = False,
        oudated_img_meta_cache = True,  
    ),
    only_update_cached_pages = False,
    fill_property= reader.FillPropertyParams(
        img_caption = True,
        img_description = True,
        text_wikitext = True,
        text_html = True,
    ),
    language_code = 'en',
    early_icons_removal = True,
)

################################################################################

print("Data Collection\n")
reader.query(filename=filename, params=query_params)

print("Data Preprocessing 1. Removing images not available on Commons\n")
preprocessor.filter_img_metadata(
    data_path=query_params.out_dir,
    offset=query_params.offset,
    limit=query_params.limit, 
    debug_info=query_params.debug_info,
    field_to_remove='on_commons',
    predicate=lambda x: ('on_commons' not in x) or x['on_commons']
)

print("Data Preproccesing 2. Removing icons\n")
preprocessor.filter_img_metadata(
    data_path=query_params.out_dir,
    offset=query_params.offset,
    limit=query_params.limit, 
    debug_info=query_params.debug_info,
    field_to_remove='is_icon',
    predicate=lambda x: ('is_icon' not in x) or (not x['is_icon'])
)

print("Data Preprocessing 3. Parsing Image Headings\n")
preprocessor.parse_image_headings(
    data_path=query_params.out_dir,
    offset=query_params.offset,
    limit=query_params.limit,
    invalidate_cache=invalidate_headings_cache,
    debug_info=query_params.debug_info,
    language_code=query_params.language_code,
)

print("Data Preprocessing 4. Generating visual features\n")
preprocessor.generate_visual_features(
    data_path=query_params.out_dir,
    offset=query_params.offset,
    limit=query_params.limit,
    invalidate_cache=invalidate_visual_features_cache,
    debug_info=query_params.debug_info,
)

print("Data Preprocessing 5. Parse image titles\n")
preprocessor.tokenize_image_titles(
    data_path=query_params.out_dir,
    offset=query_params.offset,
    limit=query_params.limit,
    invalidate_cache=invalidate_parsed_titles_cache,
    debug_info=query_params.debug_info,
)

print("Dataset collection has completed.")
