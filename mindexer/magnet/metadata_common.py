# Copyright (c) 2025 DFlexy · https://github.com/DFlexy
"""Funções puras compartilhadas entre metadata.py (sync) e metadata_async.py (async)."""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def parse_bencode_size(data: bytes) -> Optional[int]:
    """Parseia bencode parcial para extrair o tamanho do torrent."""
    try:
        match = re.search(rb'lengthi(\d+)e', data)
        if match:
            return int(match.group(1))

        matches = re.findall(rb'6:lengthi(\d+)e', data)
        if matches:
            total = sum(int(m) for m in matches)
            if total > 0:
                return total

        matches = re.findall(rb'i(\d{6,15})e', data)
        if matches:
            sizes = []
            for num_str in matches:
                num = int(num_str)
                if 1048576 <= num <= 1125899906842624:
                    sizes.append(num)
            if sizes:
                return sum(sizes)

        return None
    except Exception as e:
        logger.debug(f"Bencode parse error: {type(e).__name__}")
        return None
