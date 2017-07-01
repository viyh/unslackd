from datetime import datetime
from slackclient import SlackClient
from bs4 import BeautifulSoup
import requests
import yaml

def read_config():
    with open('unslackd.yaml', 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
    return cfg

def get_user_activity_html(user):
    url = 'https://untappd.com/user/' + user
    raw = requests.get(url).content.decode()
    return raw

def parse_item(item):
    checkin_dict = {}
    checkin_dict['checkin_id'] = item.get('data-checkin-id')
    checkin = item.select('div.checkin')[0]
    beer = checkin.select('div.top')[0].select('p.text')[0].select('a')
    try:
        checkin_dict['comment'] = checkin.select('p.comment-text')[0].text.strip()
    except:
        pass
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

def get_checkins(html):
    soup = BeautifulSoup(html, 'html.parser')
    checkins = []
    for item in soup.findAll('div', {'class': 'item'}):
        checkin_dict = parse_item(item)
        if 'date' in checkin_dict and now - checkin_dict['date'] < cfg['date_delta']:
            checkins.append(checkin_dict)
        if len(checkins) >= 5:
            break
    return checkins

def post_user_checkins(checkins):
    for checkin in checkins:
        post_slack_message(get_slack_text(checkin))
        if cfg['debug']:
            print(get_slack_text(checkin))

def get_slack_text(checkin):
    message = []
    message.append(':untappd: <https://untappd.com{}/checkin/{}|New Check-in>'.format(
        checkin['user_url'],
        checkin['checkin_id']
    ))
    message.append(' from <https://untappd.com{}|{}>'.format(
        checkin['user_url'],
        checkin['user_friendly_name']
    ))
    message.append(': <https://untappd.com{}|{}> by <https://untappd.com{}|{}>'.format(
        checkin['beer_url'],
        checkin['beer_name'],
        checkin['brewery_url'],
        checkin['brewery_name']
    ))
    if 'location_name' in checkin and 'location_url' in checkin:
        message.append(' at <https://untappd.com{}|{}>'.format(
            checkin['location_url'],
            checkin['location_name']
        ))
    if 'rating' in checkin:
        message.append(' [Rated: *{}*]'.format(checkin['rating']))
    if 'comment' in checkin:
        message.append(' - "{}"'.format(checkin['comment']))
    return ''.join(message)

def post_slack_message(message):
    sc.api_call(
        'chat.postMessage',
        channel=cfg['slack_channel'],
        text=message
    )

def main():
    for user in cfg['users']:
        user_activity_html = get_user_activity_html(user)
        checkins = get_checkins(user_activity_html)
        post_user_checkins(checkins)

if __name__ == "__main__":
    cfg = read_config()
    sc = SlackClient(cfg['slack_api_key'])
    now = int(datetime.now().timestamp())
    main()
