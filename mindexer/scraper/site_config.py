# Copyright (c) 2025 DFlexy · https://github.com/DFlexy
"""Painel do site: concentra o que precisa ser editado quando um site muda.

Cada scraper define, no topo do arquivo, um bloco como este:

    SITE = SiteConfig(
        url="https://exemplo.com/",   # endereço do site
        caminho_busca="?s=",          # como o site monta a URL de busca
        paginacao="page/{}/",         # como o site monta a URL de cada página
        seletores={                   # onde achar cada coisa no HTML
            "card": ".item",
            ...
        },
    )

Quando o site mudar de endereço ou de layout, edite SOMENTE esse bloco.

Dica: o endereço também pode ser trocado sem mexer no código, usando a
variável de ambiente SCRAPER_URL_<TIPO> (ex.: SCRAPER_URL_STARCK). Ela tem
prioridade sobre o valor definido aqui.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class SiteConfig:
    # Endereço do site (termine com "/")
    url: str
    # Sufixo da URL de busca. Ex.: "?s=" vira https://site.com/?s=matrix
    caminho_busca: str = "?s="
    # Padrão da URL de paginação. O {} é substituído pelo número da página.
    paginacao: str = "page/{}/"
    # Seletores CSS: apontam onde cada informação fica no HTML do site.
    seletores: Dict[str, str] = field(default_factory=dict)
