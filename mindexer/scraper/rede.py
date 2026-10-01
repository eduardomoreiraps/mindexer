# Copyright (c) 2025 DFlexy · https://github.com/DFlexy

import html
import re
import logging
from datetime import datetime
from utils.parsing.date_extraction import parse_date_from_string
from typing import List, Dict, Optional, Callable
from urllib.parse import quote, quote_plus, unquote, urljoin
from bs4 import BeautifulSoup
from scraper.base import BaseScraper
from scraper.site_config import SiteConfig
from utils.text.constants import STOP_WORDS
from utils.text.utils import find_year_from_text, find_sizes_from_text
from utils.logging import ScraperLogContext

logger = logging.getLogger(__name__)

_log_ctx = ScraperLogContext("Rede", logger)

# ╔═══════════════════════════════════════════════════════════════════════╗
# ║ PAINEL DO SITE — REDE                                                 ║
# ║ O site mudou de endereço ou de layout? Edite SOMENTE este bloco.      ║
# ╚═══════════════════════════════════════════════════════════════════════╝
SITE = SiteConfig(
    url="https://redestorrents.com/",
    caminho_busca="index.php?busca=",
    paginacao="pagina/{}/",
    seletores={
        # --- Listagem e resultados de busca ---
        "card": "a.cover-link, article.custom-card, .capa_lista",  # cada card de filme/série
        "link_do_card": "a",                                      # link dentro do card
        "links_paginacao": "a[href*='pagina'], a[href], .pagination a, .wp-pagenavi a",
        # --- Página do filme/série ---
        "conteudo": "main, article, div.container, div.conteudo", # bloco principal da página
        "informacoes": "div.info-pills, div#informacoes",         # bloco com a ficha (idioma, tamanho...)
        "ficha_paragrafos": "div.info-pill, div#informacoes > p",
        "links_download": "div.download-list, div.download-row, div.apenas_itemprop",
    },
)

class RedeScraper(BaseScraper):
    SCRAPER_TYPE = "rede"
    DEFAULT_BASE_URL = SITE.url
    DISPLAY_NAME = "Rede"
    
    def __init__(self, base_url: Optional[str] = None, use_flaresolverr: bool = False):
        super().__init__(base_url, use_flaresolverr)
        self.search_url = SITE.caminho_busca
        self.page_pattern = SITE.paginacao
    
    def _get_search_token(self) -> str:
        if hasattr(self, '_search_token') and self._search_token:
            return self._search_token
        doc = self.get_document(self.base_url)
        if doc:
            token_input = doc.select_one('input[name="token"]')
            if token_input and token_input.get('value'):
                self._search_token = token_input.get('value').strip()
                return self._search_token
        return ""
    
    def search(
        self,
        query: str,
        filter_func: Optional[Callable[[Dict], bool]] = None,
        skip_trackers: bool = False,
        skip_metadata: bool = False,
    ) -> List[Dict]:
        return self._default_search(
            query, filter_func, skip_trackers=skip_trackers, skip_metadata=skip_metadata
        )
    
    def _extract_links_from_page(self, doc: BeautifulSoup) -> List[str]:
        return self._extract_search_results(doc)
    
    def get_page(self, page: str = '1', max_items: Optional[int] = None, is_test: bool = False) -> List[Dict]:
        return self._default_get_page(page, max_items, is_test=is_test)
    
    def _extract_search_results(self, doc: BeautifulSoup) -> List[str]:
        links = []
        for item in doc.select(SITE.seletores["card"]):
            href = None
            if item.name == 'a' and item.get('href'):
                href = item.get('href')
            elif item.name == 'article' and item.parent and item.parent.name == 'a' and item.parent.get('href'):
                href = item.parent.get('href')
            else:
                link_elem = item.select_one(SITE.seletores["link_do_card"])
                href = link_elem.get('href') if link_elem else None

            if href:
                href = href.strip()
                if 'login.php' in href or 'redirect=' in href:
                    continue
                if not href.startswith('http'):
                    href = urljoin(self.base_url, href)
                if href not in links:
                    links.append(href)
        return links

    def _search_variations(self, query: str) -> List[str]:
        links = []
        seen_urls = set()
        variations = [query]

        query_words = query.split()

        if len(query_words) >= 2 and query_words[-1].isdigit() and len(query_words[-1]) == 4 and query_words[-1][:2] in ('19', '20'):
            without_year = ' '.join(query_words[:-1])
            if without_year not in variations:
                variations.append(without_year)

        if len(query_words) > 1 and len(query_words) < 3:
            first_word = query_words[0].lower()
            if first_word not in STOP_WORDS:
                variations.append(query_words[0])

        token = self._get_search_token()

        for variation in variations:
            if token:
                search_url = f"{self.base_url}index.php?hp_bot_check=&token={token}&busca={quote_plus(variation)}"
            else:
                search_url = f"{self.base_url}{self.search_url}{quote_plus(variation)}"

            doc = self.get_document(search_url, self.base_url)
            if not doc:
                continue

            page_links = self._extract_search_results(doc)
            for link in page_links:
                if link not in seen_urls:
                    links.append(link)
                    seen_urls.add(link)
                    if len(links) >= 15:
                        break
            if len(links) >= 15:
                break

        return links[:15]

    def _get_torrents_from_page(self, link: str) -> List[Dict]:
        absolute_link = urljoin(self.base_url, link) if link and not link.startswith('http') else link
        doc = self.get_document(absolute_link, self.base_url)
        if not doc:
            return []

        from utils.parsing.date_extraction import extract_date_from_page
        date = extract_date_from_page(doc, absolute_link, self.SCRAPER_TYPE)

        h1 = doc.select_one('h1.movie-title, h1')
        if not h1:
            self._log_structure_miss(absolute_link, 'h1.movie-title / h1')
            return []

        title_text = h1.get_text(strip=True)

        year = ''
        year_match = re.search(r'\((\d{4})\)', title_text)
        if year_match:
            year = year_match.group(1)
        else:
            for pill in doc.select('.info-pill'):
                t = pill.get_text(strip=True)
                if re.fullmatch(r'\d{4}', t):
                    year = t
                    break

        clean_title = re.sub(r'(?i)\s+torrent\b.*', '', title_text).strip()
        clean_title = re.sub(r'\s*\(\d{4}\).*', '', clean_title).strip()
        if not clean_title:
            clean_title = re.sub(r'(?i)\bdownload\b', '', title_text).strip()

        original_title = ''
        orig_elem = doc.select_one('.original-title, p.original-title')
        if orig_elem:
            orig_raw = orig_elem.get_text(strip=True)
            original_title = re.sub(r'(?i)^filme\s+', '', orig_raw).strip()

        if not original_title:
            for p in doc.select(SITE.seletores["ficha_paragrafos"]):
                p_text = p.get_text(strip=True)
                if 'Título Original:' in p_text:
                    parts = p_text.split('Título Original:')
                    if len(parts) > 1:
                        original_title = parts[1].split('Gênero')[0].split('Ano')[0].strip()
                        break

        if not original_title:
            original_title = clean_title

        title_translated_processed = clean_title if clean_title != original_title else ''

        if self._should_skip_page_by_query(
            clean_title, original_title, title_translated_processed, absolute_link,
        ):
            return []

        audio_texts = []
        for pill in doc.select('.info-pill, .badge-audio'):
            audio_texts.append(pill.get_text(strip=True))
        for name_elem in doc.select('.download-name'):
            audio_texts.append(name_elem.get_text(strip=True))
        for p in doc.select(SITE.seletores["ficha_paragrafos"]):
            audio_texts.append(p.get_text(strip=True))

        audio_html_content = ' '.join(audio_texts) + ' ' + title_text
        from utils.parsing.audio_extraction import detect_audio_from_html
        audio_info = detect_audio_from_html(audio_html_content)

        from utils.parsing.legend_extraction import extract_legenda_from_page, determine_legend_info
        legenda = extract_legenda_from_page(doc, scraper_type='rede')
        legend_info = determine_legend_info(legenda) if legenda else None

        imdb = ''
        for pill in doc.select('.info-pill'):
            m = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10', pill.get_text(strip=True))
            if m:
                imdb = m.group(1)
                break
        if not imdb:
            from utils.parsing.imdb_extraction import extract_imdb_from_soup
            imdb = extract_imdb_from_soup(doc)

        magnet_links = []
        sizes = []

        rows = doc.select('.download-row')
        if rows:
            for row in rows:
                mag_elem = row.select_one('a[href^="magnet:"]')
                mag_href = mag_elem.get('href', '') if mag_elem else ''
                if not mag_href:
                    for a in row.select('a[href]'):
                        h = a.get('href', '')
                        if 'magnet:' in h or 'download' in h.lower():
                            resolved = self._resolve_link(h)
                            if resolved and resolved.startswith('magnet:'):
                                mag_href = resolved
                                break

                if mag_href and mag_href.startswith('magnet:'):
                    name_elem = row.select_one('.download-name')
                    name_text = name_elem.get_text(strip=True) if name_elem else ''

                    if 'dn=' not in mag_href:
                        dn_parts = [original_title or clean_title]
                        if year:
                            dn_parts.append(year)
                        if name_text:
                            clean_name = re.sub(r'(?i)\bdownload\b|\btorrent\b', '', name_text).strip()
                            clean_name = re.sub(r'(\d+)ª?\s*epis[oó]dio', r'E\1', clean_name, flags=re.IGNORECASE)
                            dn_parts.append(clean_name)
                        dn_candidate = '.'.join(re.sub(r'[^a-zA-Z0-9._-]+', '.', ' '.join(dn_parts)).split('.'))
                        mag_href += f"&dn={quote(dn_candidate)}"

                    if mag_href not in magnet_links:
                        magnet_links.append(mag_href)
                        row_sizes = find_sizes_from_text(name_text)
                        sizes.append(row_sizes[0] if row_sizes else '')

        if not magnet_links:
            for a in doc.select('a[href]'):
                href = a.get('href', '')
                if href.startswith('magnet:'):
                    resolved = href
                elif 'magnet' in href.lower() or 'download' in href.lower():
                    resolved = self._resolve_link(href)
                else:
                    resolved = None

                if resolved and resolved.startswith('magnet:'):
                    if resolved not in magnet_links:
                        magnet_links.append(resolved)

        if not magnet_links:
            return []

        if not any(sizes):
            page_sizes = find_sizes_from_text(doc.get_text())
            if page_sizes:
                sizes = page_sizes

        from core.builders import build_torrents_from_magnets
        return build_torrents_from_magnets(
            magnet_links=magnet_links,
            sizes=sizes,
            page_title=clean_title,
            original_title=original_title,
            title_translated_processed=title_translated_processed,
            year=year,
            imdb=imdb,
            audio_info=audio_info,
            audio_html_content=audio_html_content,
            absolute_link=absolute_link,
            date=date,
            legend_info=legend_info,
            skip_metadata=self._skip_metadata,
            doc=doc,
            scraper_type=self.SCRAPER_TYPE,
            log_ctx=_log_ctx,
            fallback_title_priority='page',
        )


