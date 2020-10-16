import scrapy
import json
import re
from scrapers.items import ProductItem


class CaWalmartBot(scrapy.Spider):
    name = 'ca_walmart'
    allowed_domains = ['walmart.ca']
    start_urls = ['https://www.walmart.ca/en/grocery/fruits-vegetables/fruits/N-3852']
    header = {
        'Host': 'www.walmart.ca',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/json',
        'Connection': 'keep-alive'
    }

    def parse(self, response):

        for url in response.css('.product-link::attr(href)').getall():
            yield response.follow(url, callback=self.parse_front, cb_kwargs={'url': url})

        next = response.css('#loadmore::attr(href)').get()

        if next != None:
            yield response.follow(next, callback=self.parse)

    def parse_front(self, response, url):

        items = ProductItem()
        branches = {
            '3106': ['43.656422', '-79.435567'],
            '3124': ['48.412997', '-89.239717']
        }
        prod_dict = json.loads(response.css('.evlleax2 > script:nth-child(1)::text').get())

        sku = prod_dict['sku']
        description = prod_dict['description']
        name = prod_dict['name']
        brand = prod_dict['brand']['name']
        image_url = prod_dict['image']

        gral_dict = json.loads(re.findall(r'(\{.*\})', response.xpath("/html/body/script[1]/text()").get())[0])


        upc = gral_dict['entities']['skus'][sku]['upc']
        category = gral_dict['entities']['skus'][sku]['facets'][0]['value']

        for i in range(3):
            category = ' | '.join(
                [gral_dict['entities']['skus'][sku]['categories'][0]['hierarchy'][i]['displayName']['en'], category])

        package = gral_dict['entities']['skus'][sku]['description']

        items['barcodes'] = ', '.join(upc)
        items['store'] = response.xpath('/html/head/meta[10]/@content').get()
        items['category'] = category
        items['package'] = package
        items['url'] = self.start_urls[0] + url
        items['brand'] = brand
        items['image_url'] = ', '.join(image_url)
        items['description'] = description.replace('<br>', '')
        items['sku'] = sku
        items['name'] = name

        url_store = 'https://www.walmart.ca/api/product-page/find-in-store?' \
                    'latitude={}&longitude={}&lang=en&upc={}'

        for k in branches.keys():
            yield scrapy.http.Request(url_store.format(branches[k][0], branches[k][1], upc[0]),
                                      callback=self.parse_connect, cb_kwargs={'items': items},
                                      meta={'handle_httpstatus_all': True},
                                      dont_filter=False, headers=self.header)

    def parse_connect(self, response, item):
        store = json.loads(response.body)

        branch = store['info'][0]['id']
        stock = store['info'][0]['availableToSellQty']

        if 'sellPrice' not in store['info'][0]:
            price = 0
        else:
            price = store['info'][0]['sellPrice']

        item['branch'] = branch
        item['stock'] = stock
        item['price'] = price

        yield item