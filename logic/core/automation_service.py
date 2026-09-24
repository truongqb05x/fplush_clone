# -*- coding: utf-8 -*-
"""
Facade for automation_service.
Các hàm đã được tách ra các file nhỏ (group_service, keyword_service, page_service, ttc_service)
"""

from core.group_service import process_group_cycle
from core.keyword_service import process_keyword_search
from core.page_service import process_page_cycle
from core.ttc_service import process_ttc_cycle

__all__ = [
    'process_group_cycle',
    'process_keyword_search',
    'process_page_cycle',
    'process_ttc_cycle'
]
