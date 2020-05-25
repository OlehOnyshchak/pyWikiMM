# pyWikiMM
Collects a dataset of Wikipedia articles and corresponding images

## About
This is a package to collect and preprocess multimodal(text-images) dataset of Wikipedia articles. Besides collecting article content and its images, it also retrieves a gread deal of metadata such as URI, HTML-snapshot, image caption and descriptions and a lot more. Or you can get our downloaded dataset of [Featured Articles](https://en.wikipedia.org/wiki/Wikipedia:Featured_articles) from [Kaggle](https://www.kaggle.com/jacksoncrow/extended-wikipedia-multimodal-dataset)

## Installation
If Featured dataset mentioned above does not satisfy your need, you have two options to create your own dataset.
### Kaggle
The most straightforward option to create your dataset is to do it in the cloud. In that case, you can just fork our [Kaggle Notebook](https://www.kaggle.com/jacksoncrow/data-collection-demo) to avoid dealing with setting up the environment at all. In the end, you will simply download the collected dataset.
### Docker
If your dataset is too big to collect it in the cloud, we prepared docker container so that you can easily do it locally. Just follow the instructions below to build and run a docker container:
```bash
$ git clone https://github.com/OlehOnyshchak/WikipediaMultimodalDownloader.git
$ cd WikipediaMultimodalDownloader/
$ echo "Adjust parameters in `main.py` with what and how you want to download"
$ sudo docker build . -t wiki_downloader:1.0
$ WIKI_OUT_DIR="/home/oleh/data_docker" # Replace with absolute path to your local folder
$ sudo docker run -v $WIKI_OUT_DIR:/home/seluser/data wiki_downloader:1.0
```
Please note, you can avoid using `sudo` if you docker is cofigured to run without it.

## Main Features
* given list of articles as an input, downloads their content with images, enrich with a lot of metadata
* functionality extensively support cached data. So if you need to update some specific parts of your dataset, it would be done in almost optimal way
* supports all languages. You can specify Wikipedia language as an input parameter.

## Dataset structure
The high-level structure of the dataset is as follows:

    .
    +-- page1  
    |   +-- text.json  
    |   +-- img  
    |       +-- meta.json
    +-- page2  
    |   +-- text.json  
    |   +-- img  
    |       +-- meta.json
    :  
    +-- pageN 
    |   +-- text.json  
    |   +-- img  
    |       +-- meta.json

label      | description
---------  | ----------
pageN      | is the title of N-th Wikipedia page and contains all information about the page
text.json  | text of the page saved as JSON. Please refer to the details of JSON schema below.
meta.json  | a collection of all images of the page. Please refer to the details of JSON schema below.
imageN     | is the N-th image of an article, saved in `jpg` format where the width of each image is set to 600px. Name of the image is md5 hashcode of original image title. 
 
### text.JSON Schema
Below you see an example of how data is stored:

    {
      "title": "Naval Battle of Guadalcanal",
      "id": 405411,
      "url": "https://en.wikipedia.org/wiki/Naval_Battle_of_Guadalcanal",
      "html": "... <title>Naval Battle of Guadalcanal - Wikipedia</title>\n ...",
      "wikitext": "... The '''Naval Battle of Guadalcanal''', sometimes referred to as ...",
    }
key           | description
------------  | --------------
title         | page title
id            | unique page id
url           | url of a page on Wikipedia
html          | HTML content of the article
wikitext      | wikitext content of the article
    
Please note that @html and @wikitext properties represent the same information in different formats, so just choose the one which is easier to parse in your circumstances.


### meta.JSON Schema

    {
      "img_meta": [
        {
          "filename": "702105f83a2aa0d2a89447be6b61c624.jpg",
          "title": "IronbottomSound.jpg",
          "parsed_title": "ironbottom sound",
          "url": "https://en.wikipedia.org/wiki/File%3AIronbottomSound.jpg",
          "is_icon": False,
          "on_commons": True,
          "description": "A U.S. destroyer steams up what later became known as ...",
          "caption": "Ironbottom Sound. The majority of the warship surface ...",
          "headings": ['Naval Battle of Guadalcanal', 'First Naval Battle of Guadalcanal', ...],
          "features": ['4.8618264', '0.49436468', '7.0841103', '2.7377882', '2.1305492', ...],
         },
         ...
       ]
    }

key           | description
------------  | --------------
filename      |  unique image id, md5 hashcode of original image title
title         |  image title retrieved from Commons, if applicable
parsed_title  | image title split into words, i.e. "helloWorld.jpg" -> "hello world"
url           | url of an image on Wikipedia
is_icon       | True if image is an icon, e.g. category icon. We assume that image is an icon if you cannot load a preview on Wikipedia after clicking on it
on_commons    | True if image is available from Wikimedia Commons dataset
description   | description of an image parsed from Wikimedia Commons page, if available
caption       | caption of an image parsed from Wikipedia article, if available
headings      | list of all parent headings of image in Wikipedia article. The first element is a top-most heading
features      | output of 5-th convolutional layer of ResNet152 trained on ImageNet dataset. That output of shape (19, 24, 2048) is then max-pooled to a shape (2048,). Features taken from original images downloaded in `jpeg` format with fixed width of 600px. Practically, it is a list of floats with len = 2048

## Further Reading
This project was developed as a part of ["Image Recommendation for Wikipedia Articles"](http://dx.doi.org/10.13140/RG.2.2.17463.27042) thesis, so you can find more context as well as application of this downloader there.

## Acknowledgments
Special thanks to [Miriam Redi](http://www.visionresearchwitch.com/) for actively mentoring me in this project.

## Feedback is a Gift
If you were interacting with this library, please do share your feedback. If something isn't working, isn't clear or is missing, please open an issue and let me know. Or if you found this library useful, please star this repo or just post a comment into feedback thread in Issues tab. Your comments will help me to improve the project, your starts will help me to identify how useful it is.
