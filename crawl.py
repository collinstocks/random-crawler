#!/usr/bin/env python3

import http.cookiejar
import random
import traceback
import urllib.error
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup


class Opener(object):
    def __init__(self, timeout):
        self.timeout = timeout
        cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def open(self, url):
        response = self.opener.open(url, timeout=self.timeout)
        return response


class LinkGetter(Opener):
    def get_links(self, url):
        with self.open(url) as response:
            doc = response.read(1000000)
        soup = BeautifulSoup(doc, 'html.parser')
        rel_links = {tag['href'] for tag in soup.find_all('a') if tag.get('href')}
        abs_links = {urllib.parse.urljoin(url, rel_link) for rel_link in rel_links}
        http_links = {url for url in abs_links if urllib.parse.urlsplit(url).scheme.lower() in ['http', 'https']}
        return http_links


class RandomHistory(object):
    def __init__(self, history_size):
        self.history_size = history_size
        self.history = []
        self.history_dict = {}

    def __contains__(self, item):
        return item in self.history_dict

    def __len__(self):
        return len(self.history)

    def add(self, item):
        if item in self.history_dict:
            return
        if len(self.history) == self.history_size:
            index = random.randrange(self.history_size)
            del self.history_dict[self.history[index]]
            self.history[index] = item
            self.history_dict[item] = index
        else:
            self.history_dict[item] = len(self.history)
            self.history.append(item)

    def replace(self, old_item, new_item):
        if old_item not in self.history_dict:
            self.add(new_item)
        else:
            index = self.history_dict[old_item]
            del self.history_dict[old_item]
            self.history[index] = new_item
            self.history_dict[new_item] = index

    def get(self):
        return random.choice(self.history)


class RandomSpider(object):
    def __init__(
        self, seed='https://en.wikipedia.org/wiki/Main_Page', history_size=10000, clear_cookie_period=10000,
        timeout=10, steps_at_a_time=3, verbose=False
    ):
        self.seed = seed
        self.timeout = timeout
        self.link_getter = LinkGetter(timeout=self.timeout)
        self.history = RandomHistory(history_size)
        self.history.add(seed)
        self.clear_cookie_period = clear_cookie_period
        self.step_counter = 0
        self.steps_at_a_time = steps_at_a_time
        self.verbose = verbose

    def clear_cookies(self):
        self.link_getter = LinkGetter(timeout=self.timeout)

    def visit(self, url):
        if self.verbose:
            print('visiting', url)
        url = url.split('#')[0]
        url_netloc = urllib.parse.urlsplit(url).netloc
        self.step_counter += 1
        links = list(self.link_getter.get_links(url))
        internal_links = set()
        external_links = set()
        for link in links:
            link = link.split('#')[0]
            if link == url:
                continue
            link_netloc = urllib.parse.urlsplit(link).netloc
            if url_netloc == link_netloc:
                internal_links.add(link)
            else:
                external_links.add(link)
        return internal_links, external_links

    def crawl_steps(self, steps):
        url = self.history.get()
        internal_links, external_links = self.visit(url)
        for i in range(steps):
            if len(internal_links) and random.random() < 0.5:
                next_url = random.choice(list(internal_links))
                internal_links, external_links = self.visit(next_url)
                self.history.replace(url, next_url)  # Add to history after successful visit.
                url = next_url
            elif len(external_links):
                next_url = random.choice(list(external_links))
                internal_links, external_links = self.visit(next_url)
                self.history.add(next_url)
                url = next_url
        return url

    def crawl_forever(self):
        while True:
            if random.random() < 0.1:
                self.history.add(self.seed)  # Reseed periodically.
            if random.random() < 1. / self.clear_cookie_period:
                self.clear_cookies()
            try:
                if self.verbose:
                    print('steps: {}, history: {}'.format(self.step_counter, len(self.history)))
                self.crawl_steps(self.steps_at_a_time)
            except Exception:
                traceback.print_exc()


RandomSpider(verbose=True).crawl_forever()
