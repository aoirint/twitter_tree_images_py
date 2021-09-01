#!/usr/bin/env python3

import os
import json
import requests
import tempfile
from pathlib import Path
import shutil

def dl_tweet_tree_images(
    tweet_id: str,
    output_dir: Path,
    token: str,
):
    session = requests.Session()

    headers = {
      'Authorization': f'Bearer {token}'
    }

    # https://developer.twitter.com/en/docs/twitter-api/v1/tweets/post-and-engage/api-reference/get-statuses-show-id
    res_tweets = session.get(f'https://api.twitter.com/1.1/statuses/show.json?id={tweet_id}', headers=headers)
    tweet = json.loads(res_tweets.text)
    author_screen_name = tweet['user']['screen_name']

    params = {
        'q': f'from:{author_screen_name}',
        'count': 100,
        'result_type': 'recent',
        'include_entities': 1,
    }

    # https://developer.twitter.com/en/docs/twitter-api/v1/tweets/search/api-reference/get-search-tweets
    res_self_mentions = session.get('https://api.twitter.com/1.1/search/tweets.json', headers=headers, params=params)
    self_mentions = json.loads(res_self_mentions.text)

    thread_ids = set()
    thread_ids.add(str(tweet_id))

    print(tweet_id, tweet['text'])

    self_replies = []
    self_replies.append(tweet)
    for mention in reversed(self_mentions['statuses']):
        mention_tweet_id = str(mention['id'])
        in_reply_to_status_id = str(mention['in_reply_to_status_id'])

        if in_reply_to_status_id is not None and in_reply_to_status_id in thread_ids:
            thread_ids.add(mention_tweet_id)
            self_replies.append(mention)

    print(':Self Reply List')
    for self_reply in self_replies:
        print(self_reply['id'], self_reply['text'], '=>', self_reply['in_reply_to_status_id'])


    download_index = 1
    downloaded_url_list = set()
    print(':Media List')
    for self_reply in self_replies:
        def download_photos(entities):
            nonlocal download_index, downloaded_url_list

            media = entities.get('media')
            if media is None:
                return

            photos = filter(lambda medium: medium['type'] == 'photo', media)
            for photo in photos:
                photo_url = photo['media_url_https']
                if photo_url in downloaded_url_list:
                    continue

                print(photo_url)

                tweet_dir = output_dir / f'{author_screen_name}_{tweet_id}'
                tweet_dir.mkdir(parents=True, exist_ok=True)

                filename = Path(photo_url).name
                new_filename = f'{tweet_id}_{download_index:03}_{filename}'
                output_path = tweet_dir / new_filename
                if output_path.exists():
                    continue

                with tempfile.NamedTemporaryFile() as fp:
                    photo_res = session.get(photo_url, stream=True)
                    shutil.copyfileobj(photo_res.raw, fp)
                    shutil.copy(fp.name, output_path)

                    download_index += 1
                    downloaded_url_list.add(photo_url)

        entities = self_reply.get('entities')
        if entities is not None:
            download_photos(entities)

        extended_entities = self_reply.get('extended_entities')
        if extended_entities is not None:
            download_photos(extended_entities)
