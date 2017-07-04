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
    return requests.get(url).content.decode()

def get_checkin_id(item):
    return item.get('data-checkin-id')

def get_checkin_rating(item):
    try:
        rating = item.select('span.rating')[0]['class'][-1].lstrip('r')
        return rating[:1] + '.' + rating[1:]
    except:
        return '---'

def get_checkin_badges(item):
    badge_list = []
    try:
        badges = item.select('span.badge')
        for badge in badges:
            badge_list.append(
                {
                    'badge_name': badge.select('img.lazy')[0].get('alt'),
                    'badge_url': badge.select('img.lazy')[0].get('data-original')
                }
            )
    except:
        pass
    return badge_list

def get_checkin_beer(item):
    beer_dict = {}
    checkin = item.select('div.checkin')[0]
    beer = checkin.select('div.top')[0].select('p.text')[0].select('a')
    try:
        beer_dict['comment'] = checkin.select('p.comment-text')[0].text.strip()
    except:
        pass
    beer_dict['user_friendly_name'] = beer[0].text
    beer_dict['user_url'] = beer[0].get('href')
    beer_dict['user_friendly_name'] = beer[0].text
    beer_dict['user_url'] = beer[0].get('href')
    beer_dict['beer_name'] = beer[1].text
    beer_dict['beer_url'] = beer[1].get('href')
    beer_dict['brewery_name'] = beer[2].text
    beer_dict['brewery_url'] = beer[2].get('href')
    if len(beer) >= 4:
        beer_dict['location_name'] = beer[3].text
        beer_dict['location_url'] = beer[3].get('href')
    return beer_dict

def get_checkin_date(item):
    return int(datetime.strptime(item.select('a.timezoner')[0].text, '%a, %d %b %Y %H:%M:%S %z').timestamp())

def get_checkin_url(item):
    return item.select('a.timezoner')[0]['href']

def parse_item(item):
    checkin_dict = {}
    checkin_dict['checkin_id'] = get_checkin_id(item)
    checkin_dict = {**checkin_dict, **get_checkin_beer(item)}
    checkin_dict['rating'] = get_checkin_rating(item)
    checkin_dict['badges'] = get_checkin_badges(item)
    checkin_dict['date'] = get_checkin_date(item)
    checkin_dict['checkin_url'] = get_checkin_url(item)
    checkin_dict['badges'] = get_checkin_badges(item)
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
        post_slack_message(get_slack_text(checkin), get_slack_attachments(checkin))
        if cfg['debug']:
            print(get_slack_text(checkin), get_slack_attachments(checkin))


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
    if checkin.get('location_name') and checkin.get('location_url'):
        message.append(' at <https://untappd.com{}|{}>'.format(
            checkin['location_url'],
            checkin['location_name']
        ))
    if checkin.get('rating'):
        message.append(' [Rated: *{}*]'.format(checkin['rating']))
    if checkin.get('comment'):
        message.append(' - "{}"'.format(checkin['comment']))
    return ''.join(message)

def get_slack_attachments(checkin):
    attachments = []
    if checkin.get('badges'):
        for badge in checkin['badges']:
            attachments.append(
                {
                    'title': badge['badge_name'],
                    'image_url': badge['badge_url']

                }
            )
    return attachments

def post_slack_message(message, attachments):
    sc.api_call(
        'chat.postMessage',
        channel=cfg['slack_channel'],
        text=message,
        attachments=attachments
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
