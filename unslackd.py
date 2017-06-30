from datetime import datetime
from slackclient import SlackClient
from bs4 import BeautifulSoup
import requests
import yaml

def read_config():
    with open('untappd.yaml', 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
    return cfg

def get_html(user):
    url = 'https://untappd.com/user/' + user
    raw = requests.get(url).content.decode()
    return raw

def parse_item(item):
    checkin_dict = {}
    checkin_dict['checkin_id'] = item.get('data-checkin-id')
    checkin = item.select('div.checkin')[0]
    beer = checkin.select('div.top')[0].select('p.text')[0].select('a')
    checkin_dict['user_friendly_name'] = beer[0].text
    checkin_dict['user_url'] = beer[0].get('href')
    checkin_dict['user_friendly_name'] = beer[0].text
    checkin_dict['user_url'] = beer[0].get('href')
    checkin_dict['beer_name'] = beer[1].text
    checkin_dict['beer_url'] = beer[1].get('href')
    checkin_dict['brewery_name'] = beer[2].text
    checkin_dict['brewery_url'] = beer[2].get('href')
    if len(beer) >= 4:
        checkin_dict['location_name'] = beer[3].text
        checkin_dict['location_url'] = beer[3].get('href')
    try:
        rating = item.select('span.rating')[0]['class'][-1].lstrip('r')
        checkin_dict['rating'] = rating[:1] + '.' + rating[1:]
    except:
        checkin_dict['rating'] = '---'
    checkin_dict['date'] = int(datetime.strptime(item.select('a.timezoner')[0].text, '%a, %d %b %Y %H:%M:%S %z').timestamp())
    checkin_dict['checkin_url'] = item.select('a.timezoner')[0]['href']
    return checkin_dict

def parse_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    checkins = []
    for item in soup.findAll('div', {'class': 'item'}):
        checkin_dict = parse_item(item)
        if 'date' in checkin_dict and now - checkin_dict['date'] < cfg['date_delta']:
            checkins.append(checkin_dict)
        if len(checkins) >= 5:
            break
    return checkins

def get_slack_text(checkin):
    message = ':untappd: <https://untappd.com' + checkin['user_url'] + '/checkin/' + checkin['checkin_id'] + \
        '|New Check-in> from <https://untappd.com' + checkin['user_url'] + '|' + checkin['user_friendly_name'] + \
        '>: <https://untappd.com' + checkin['beer_url'] + '|' + checkin['beer_name'] + \
        '> by <https://untappd.com' + checkin['brewery_url'] + '|' + checkin['brewery_name'] + '>'
    if 'location_name' in checkin:
        message = message + ' at <https://untappd.com' + checkin['location_url'] + '|' + checkin['location_name'] + '>'
    if 'rating' in checkin:
        message = message + ' [Rated: *' + checkin['rating'] + '*]'
    return message

def main():
    for user in cfg['users']:
        html = get_html(user)
        for checkin in parse_html(html):
            sc.api_call(
                'chat.postMessage',
                channel=cfg['slack_channel'],
                text=get_slack_text(checkin)
            )
            if cfg['debug']:
                print(get_slack_text(checkin))

if __name__ == "__main__":
    cfg = read_config()
    sc = SlackClient(cfg['slack_api_key'])
    now = int(datetime.now().timestamp())
    main()
