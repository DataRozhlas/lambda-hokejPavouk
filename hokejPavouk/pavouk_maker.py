from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import io
import boto3
import hashlib
import time
import random
from decimal import *

staty = {
    'at': 'Rakousko',
    'ca': 'Kanada',
    'ch': 'Švýcarsko',
    'cz': 'Česko',
    'de': 'Německo',
    'dk': 'Dánsko ',
    'fi': 'Finsko',
    'fr': 'Francie',
    'gb': 'Británie',
    'it': 'Itálie',
    'lv': 'Lotyšsko',
    'no': 'Norsko',
    'ru': 'Rusko',
    'se': 'Švédsko',
    'sk': 'Slovensko',
    'us': 'USA',
}

s3 = boto3.client('s3')
bucket = boto3.resource('s3').Bucket('datarozhlas')

dyn = boto3.resource('dynamodb', region_name='eu-central-1')
table = dyn.Table('hokej19-pavouk')

share_tmpl = '''<!DOCTYPE html>
    <meta charset="UTF-8">
    <meta property="og:url" content="{0}" />
    <meta property="og:type" content="article" />
    <meta property="og:title" content="Šampionát letos vyhraje {1}" />
    <meta property="og:description" content="Tipněte si, jak dopadne mistrovství světa v hokeji!" />
    <meta property="og:image" content="{2}" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="628" />
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:site" content="@irozhlascz">
    <meta name="twitter:creator" content="@datarozhlas">
    <meta name="twitter:title" content="Šampionát letos vyhraje {1}">
    <meta name="twitter:description" content="Tipněte si, jak dopadne mistrovství světa v hokeji!">
    <meta name="twitter:image" content="{2}">
    <script>window.location.replace("https://www.irozhlas.cz/zpravy-nahled/ms-hokej-2018-tip");</script>'''
    
# 0 URL sharehtml, 1 jmeno mistra, 2 shareimg

locs = [
    (205, 103),
    (205, 150),
    (205, 230),
    (205, 278),
    (205, 378),
    (205, 427),
    (205, 507),
    (205, 555),
    (443, 168),
    (443, 215),
    (443, 444),
    (443, 491),
    (680, 234),
    (680, 280),
    (680, 417),
    (680, 466),
    (915, 256),
]

def shift(tu):
    return (tu[0] - 40, tu[1])

def make_image(event, context):
    # zapsat tip do DB
    table.put_item(
       Item={
            'uid': str(time.time()) + '_' + str(random.randint(0, 999999999)),
            'tstamp': Decimal(time.time()),
            'tip': event,
        }
    )
    
    # overit existenci obrazku
    h = hashlib.md5()
    h.update(str(event[0:-1]).encode())
    key = 'mistr-hokej-19/' + h.hexdigest() + '.html'
    
    objs = list(bucket.objects.filter(Prefix=key))
    if len(objs) > 0 and objs[0].key == key:
        return 'https://data.irozhlas.cz/' + key

    # vytvorit obrazek a sharehtml
    pattern = Image.open('./imgs/canvas.jpg', 'r').convert('RGBA')
    draw = ImageDraw.Draw(pattern,'RGBA')
    font = ImageFont.truetype('Arial.ttf', 18)

    for i in range(0, 16):
        draw.text(locs[i], staty[event[i]], font=font, fill='black')
        
        flag = Image.open('./imgs/' + event[i] + '.png', 'r').convert('RGBA')
        pattern.paste(flag, box=shift(locs[i]), mask=flag)
    
    draw.text(locs[16], staty[event[16]], font=font, fill='white') # vitez bilou barvou
    flag = Image.open('./imgs/' + event[16] + '.png', 'r').convert('RGBA')
    pattern.paste(flag, box=shift(locs[16]), mask=flag)
    
    #zapsat obrazek
    out_img = io.BytesIO()
    pattern.save(out_img, format='PNG')

    s3.put_object(Bucket='datarozhlas', 
                Key=key.replace('.html', '.png'),
                Body=out_img.getvalue(), 
                ACL='public-read', 
                ContentType='image/png')
                            
    # zapsat html
    s3.put_object(Bucket='datarozhlas', 
                Key=key,
                Body=share_tmpl.format(
                    'https://data.irozhlas.cz/' + key,
                    staty[event[-2]],
                    'https://data.irozhlas.cz/' + key.replace('.html', '.png')
                ), 
                ACL='public-read', 
                ContentType='text/html')
    
    return 'https://data.irozhlas.cz/' + key