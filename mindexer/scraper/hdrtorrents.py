# Copyright (c) 2025 DFlexy · https://github.com/DFlexy

import html
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Callable
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from scraper.base import BaseScraper
from scraper.site_config import SiteConfig
from utils.text.utils import find_year_from_text, find_sizes_from_text
from utils.parsing.date_extraction import extract_date_from_page, parse_date_from_string
from utils.parsing.audio_extraction import detect_audio_from_idioma_text
from utils.parsing.imdb_extraction import extract_imdb_from_soup
from utils.logging import ScraperLogContext
from core.builders import build_torrents_from_magnets

logger = logging.getLogger(__name__)

_log_ctx = ScraperLogContext("HdrTorrents", logger)

# ╔═══════════════════════════════════════════════════════════════════════╗
# ║ PAINEL DO SITE — HDR TORRENTS                                         ║
# ║ O site mudou de endereço ou de layout? Edite SOMENTE este bloco.      ║
# ╚═══════════════════════════════════════════════════════════════════════╝
SITE = SiteConfig(
    url="https://hdrtorrents.net/",
    caminho_busca="?busca=",
    paginacao="pagina/{}/",
    seletores={
        # --- Listagem e busca ---
        "card": "a.media-card-link",
        # --- Página do filme/série ---
        "titulo": "h1",
        "specs_container": "dl.item-specs",
        "downloads_container": ".item-downloads",
        "download_row": ".download-row",
        "download_name": ".download-name",
    },
)


class HdrTorrentsScraper(BaseScraper):
    SCRAPER_TYPE = "hdrtorrents"
    DEFAULT_BASE_URL = SITE.url
    DISPLAY_NAME = "HDR Torrents"
    USE_FLARESOLVERR_DEFAULT = False

    def __init__(self, base_url: Optional[str] = None, use_flaresolverr: bool = False):
        super().__init__(base_url, use_flaresolverr)
        self.search_url = SITE.caminho_busca
        self.page_pattern = SITE.paginacao

    def _extract_links_from_page(self, doc: BeautifulSoup) -> List[str]:
        """Extrai links de posts da página inicial ou categorias."""
        return self._collect_post_links(doc)

    def _extract_search_results(self, doc: BeautifulSoup) -> List[str]:
        """Extrai links de posts da página de resultados de busca."""
        return self._collect_post_links(doc)

    def _collect_post_links(self, doc: BeautifulSoup) -> List[str]:
        links: List[str] = []
        seen: set = set()

        for a in doc.select(SITE.seletores["card"]):
            href = (a.get('href') or '').strip()
            if not href or href in seen:
                continue
            if '-torrent-download/' in href:
                full_url = urljoin(self.base_url, href)
                seen.add(href)
                links.append(full_url)

        # Fallback genérico caso o seletor mude
        if not links:
            for a in doc.find_all('a', href=True):
                href = a['href'].strip()
                if '-torrent-download/' in href and href not in seen:
                    full_url = urljoin(self.base_url, href)
                    seen.add(href)
                    links.append(full_url)

        return links

    def _filter_links_by_result_titles(self, doc: BeautifulSoup, links: List[str], query: str) -> List[str]:
        # Sonarr/Radarr pesquisam frequentemente com títulos originais em inglês,
        # enquanto os cards da busca trazem o título em português. O filtro definitivo
        # é feito em _should_skip_page_by_query após consultar a Ficha Técnica.
        return links

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

    def get_page(self, page: str = '1', max_items: Optional[int] = None, is_test: bool = False) -> List[Dict]:
        return self._default_get_page(page, max_items, is_test=is_test)

    def _get_torrents_from_page(self, link: str) -> List[Dict]:
        absolute_link = urljoin(self.base_url, link) if link and not link.startswith('http') else link
        doc = self.get_document(absolute_link, self.base_url)
        if not doc:
            return []

        # 1. Título da página
        raw_page_title = ''
        title_elem = doc.select_one(SITE.seletores["titulo"])
        if title_elem:
            raw_page_title = title_elem.get_text(strip=True)

        # Limpar sufixos como "(2025) • Torrent Dual Áudio • 1080p"
        page_title = re.sub(r'\s*[\(•·\|].*$', '', raw_page_title).strip()
        if not page_title:
            page_title = raw_page_title

        # 2. Extração da Ficha Técnica (<dl class="item-specs">)
        specs: Dict[str, str] = {}
        for div in doc.select(f'{SITE.seletores["specs_container"]} > div'):
            dt = div.find('dt')
            dd = div.find('dd')
            if dt and dd:
                key = dt.get_text(strip=True).lower()
                val = dd.get_text(' ', strip=True)
                specs[key] = val

        original_title = (
            specs.get('título original')
            or specs.get('titulo original')
            or page_title
        )
        original_title = html.unescape(original_title).strip()

        # Filtrar páginas que não batem com a query ativa (respeitando título em PT e original)
        if self._should_skip_page_by_query(page_title, original_title, '', absolute_link):
            return []

        # Ano
        year = specs.get('lançamento') or specs.get('lancamento') or specs.get('ano') or ''
        if not year:
            year = find_year_from_text(raw_page_title, original_title) or ''

        # Idiomas / Áudio
        audio_text = specs.get('idiomas') or specs.get('áudio') or specs.get('audio') or ''
        audio_info = None
        if audio_text:
            audio_info = detect_audio_from_idioma_text(audio_text)

        # Fallback de áudio pelo título da página se não definido na ficha
        if not audio_info:
            raw_lower = raw_page_title.lower()
            if 'dual' in raw_lower:
                audio_info = 'Dual'
            elif 'dublado' in raw_lower:
                audio_info = 'Dublado'
            elif 'legendado' in raw_lower:
                audio_info = 'Legendado'
            elif 'nacional' in raw_lower:
                audio_info = 'Nacional'

        audio_html_content = audio_text or raw_page_title

        # Qualidade e Tamanho
        sizes = []
        size_spec = specs.get('tamanho') or ''
        if size_spec:
            sizes.extend(find_sizes_from_text(size_spec))

        for row_el in doc.select(SITE.seletores["download_row"]):
            row_text = row_el.get_text(' ', strip=True)
            sizes.extend(find_sizes_from_text(row_text))

        sizes = list(dict.fromkeys(sizes))

        # IMDb
        imdb = specs.get('imdb') or ''
        if not imdb:
            imdb = extract_imdb_from_soup(doc)

        # Data de publicação
        date = extract_date_from_page(doc, absolute_link, self.SCRAPER_TYPE)
        if not date:
            date_match = re.search(r'(?i)Atualizado em\s+([^\n<]+)', doc.get_text())
            if date_match:
                date = parse_date_from_string(date_match.group(1).strip())

        # 3. Extração dos links magnéticos
        magnet_links = []
        download_rows = doc.select(SITE.seletores["download_row"])
        if download_rows:
            for row in download_rows:
                mag_a = row.find('a', href=lambda h: h and h.startswith('magnet:'))
                if mag_a:
                    mag_href = mag_a.get('href', '').strip()
                    if mag_href and mag_href not in magnet_links:
                        magnet_links.append(mag_href)

        # Fallback se não encontrar download-row específico
        if not magnet_links:
            for a in doc.find_all('a', href=lambda h: h and h.startswith('magnet:')):
                mag_href = a.get('href', '').strip()
                if mag_href and mag_href not in magnet_links:
                    magnet_links.append(mag_href)

        if not magnet_links:
            return []

        # 4. Construção dos objetos de torrent
        return build_torrents_from_magnets(
            magnet_links=magnet_links,
            sizes=sizes,
            page_title=page_title,
            original_title=original_title,
            title_translated_processed='',
            year=year,
            imdb=imdb,
            audio_info=audio_info,
            audio_html_content=audio_html_content,
            absolute_link=absolute_link,
            date=date,
            legend_info=None,
            skip_metadata=self._skip_metadata,
            doc=doc,
            scraper_type=self.SCRAPER_TYPE,
            log_ctx=_log_ctx,
            fallback_title_priority='page',
            imdb_default='',
        )
