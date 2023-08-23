from datetime import datetime
import re

import scrapy

from ..items import QuotetutorialItem


def handlePriceData(price_data):
    new_price_data = []
    for price in price_data:
        new_price = "".join(price.split())
        new_price = re.findall(r'\b\d+.\d+\b', new_price)
        return float(new_price[0])
    return new_price_data


def parseTitle(title):
    if 'мг' in title[0] or 'мл' in title[0] or 'гр' in title[0] or len(re.findall(r'\b\d+[ ]*г', title[0])) != 0:
        weight = re.findall(r'\b\d+[ ]*[мг]*[ ]*\+[ ]*\d+[ ]*мг\b|'
                            r'\b\d+[ ]*[мл]*[ ]*\+[ ]*\d+[ ]*мл\b|'
                            r'\b\d+[ ]*[г]*[ ]*\+[ ]*\d+[ ]*г\b|'
                            r'\b\d+[ ]*[гр]*[ ]*\+[ ]*\d+[ ]*гр\b|'
                            r'\b\d+[ ]*[мг|мл|г|гр]+\b', title[0])
        new_title = re.sub(r'\b\d+[ ]*[мг]*[ ]*\+[ ]*\d+[ ]*мг\b|'
                           r'\b\d+[ ]*[мл]*[ ]*\+[ ]*\d+[ ]*мл\b|'
                           r'\b\d+[ ]*[г]*[ ]*\+[ ]*\d+[ ]*г\b|'
                           r'\b\d+[ ]*[гр]*[ ]*\+[ ]*\d+[ ]*гр\b|'
                           r'\b\d+[ ]*[мг|мл|г|гр]+\b', '',
                           title[0])
        return [new_title + ', ' + weight[0]]
    return title


class TestSpider(scrapy.Spider):
    name = 'test'
    current_category_index = 0
    current_page_index = 12
    start_urls = [
        'https://apteka-ot-sklada.ru/catalog/medikamenty-i-bady%2Fdermatologiya%2Fdermatit_-ekzema?start=0',
    ]
    categories = ['/catalog/medikamenty-i-bady%2Fdermatologiya%2Fdermatit_-ekzema',
                  '/catalog/medikamenty-i-bady/zabolevaniya-zhkt/sredstva-ot-izzhogi',
                  '/catalog/medikamenty-i-bady/prostudnye-zabolevaniya/ot-boli-v-gorle-tabletki',
                  ]

    def parse(self, response):
        blocks = response.css('.goods-grid__cell_size_3')
        sections_to_handle = response.css(
            '.ui-breadcrumbs__item~ .ui-breadcrumbs__item+ .ui-breadcrumbs__item span::text').extract()
        section = list(filter(len, map(str.strip, sections_to_handle)))
        if len(blocks) != 0:
            for block in blocks:
                current_datetime = datetime.now()
                current_timestamp = datetime.timestamp(current_datetime)
                timestamp = current_timestamp
                rpc = None  # There is no unique product code
                url = 'https://apteka-ot-sklada.ru' + block.css('.text_weight_medium a::attr(href)').get()
                title = block.css('.goods-card__link span::text').extract()
                new_title = parseTitle(title)
                title = new_title
                marketing_tags = block.css('.ui-tag_theme_secondary::text').extract()
                brand = None  # There is no product brand or brand name only in the picture
                in_stock = True if len(block.css('.goods-card__delivery-availability .ui-link__text')) != 0 else False
                stock = {'in_stock': in_stock,
                         'count': 0}
                yield scrapy.Request(url, callback=self.parseProductPage, meta={
                    'section': section,
                    'timestamp': timestamp,
                    'RPC': rpc,
                    'url': url,
                    'title': title,
                    'marketing_tags': marketing_tags,
                    'brand': brand,
                    'stock': stock,
                })

            next_page = 'https://apteka-ot-sklada.ru' + TestSpider.categories[
                TestSpider.current_category_index] + '?start=' + str(TestSpider.current_page_index)
            TestSpider.current_page_index += 12
            yield response.follow(next_page, callback=self.parse)
        elif TestSpider.current_category_index < 2:
            TestSpider.current_page_index = 12
            next_page = 'https://apteka-ot-sklada.ru' + TestSpider.categories[TestSpider.current_category_index]
            TestSpider.current_category_index += 1
            yield response.follow(next_page, callback=self.parse)

    def parseProductPage(self, response):
        items = QuotetutorialItem()
        store_blocks = response.css('.pickpoint-row')
        price_data = None
        if len(store_blocks) != 0:
            price_data_to_handle = store_blocks.css('.text_size_title::text').extract()
            price_data = handlePriceData(price_data_to_handle)
        main_image = response.css('.goods-gallery__active-picture-area_gallery_trigger img::attr(src)').get()
        main_image = 'https://apteka-ot-sklada.ru' + main_image
        set_images_to_handle = response.css('.goods-gallery__preview-item+ .goods-gallery__preview-item'
                                            ' .goods-gallery__preview img::attr(src)').extract()
        set_images = []
        if set_images_to_handle is not None:
            for img_to_handle in set_images_to_handle:
                img = 'https://apteka-ot-sklada.ru' + img_to_handle
                set_images.append(img)

        description = ' '.join(response.css('#description *::text').extract())
        country = response.css('.page-header__description span:nth-child(1)::text').get()
        company = response.css('.page-header__description span:nth-child(2)::text').get()
        items['section'] = response.meta['section']
        items['timestamp'] = response.meta['timestamp']
        items['RPC'] = response.meta['RPC']
        items['url'] = response.meta['url']
        items['title'] = response.meta['title']
        items['marketing_tags'] = response.meta['marketing_tags']
        items['brand'] = response.meta['brand']
        items['stock'] = response.meta['stock']
        items['price_data'] = {'original': price_data}
        items['assets'] = {
            'main_image': main_image,
            'set_images': set_images,
            'view360': None,  # There is no view360
            'video': None  # There is no video
        }
        items['metadata'] = {
            '__description': description,
            'СТРАНА ПРОИЗВОДИТЕЛЬ': country,
            'КОМПАНИЯ ПРОИЗВОДИТЕЛЬ': company
        }
        items['variants'] = 1
        yield items
