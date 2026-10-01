# Copyright (c) 2025 DFlexy · https://github.com/DFlexy

from flask import Flask, render_template, make_response
from api.handlers import index_handler, indexer_handler

def register_routes(app: Flask):
    app.add_url_rule('/', 'index', index_handler, methods=['GET'])
    app.add_url_rule('/indexer', 'indexer', lambda: indexer_handler(None), methods=['GET'])
    app.add_url_rule('/indexers/<site_name>', 'indexer_by_site', indexer_handler, methods=['GET'])
    app.add_url_rule('/api', 'search_page', search_page_handler, methods=['GET'])
    app.add_url_rule('/debug/fetch', 'debug_fetch', debug_fetch_handler, methods=['GET'])
    app.add_url_rule('/debug/scraper/<site_name>', 'debug_scraper', debug_scraper_handler, methods=['GET'])

def debug_scraper_handler(site_name):
    from flask import request, jsonify
    import traceback
    from scraper import create_scraper
    method = request.args.get('method', 'get_page')
    q = request.args.get('q', '')
    page = request.args.get('page', '1')
    use_fs = request.args.get('use_flaresolverr', 'false').lower() == 'true'
    try:
        scraper = create_scraper(site_name, use_flaresolverr=use_fs)
        if method == 'get_page':
            res = scraper.get_page(page=page)
        elif method == 'search':
            res = scraper.search(query=q)
        elif method == 'links':
            url = request.args.get('url', scraper.base_url)
            doc = scraper.get_document(url)
            if not doc:
                return jsonify({'error': 'doc is None', 'fetched_html_len': len(scraper._get_fetched_html() or '')})
            links = scraper._extract_links_from_page(doc)
            return jsonify({'links_count': len(links), 'links': links[:10]})
        return jsonify({'count': len(res), 'results': res[:5]})
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

def debug_fetch_handler():
    from flask import request, jsonify
    import requests, traceback
    target = request.args.get('url', 'https://www.starck-oficial.com/')
    try:
        s = requests.Session()
        s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        r = s.get(target, timeout=10)
        return jsonify({'status': r.status_code, 'len': len(r.text), 'snippet': r.text[:300]})
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

def search_page_handler():
    response = make_response(render_template('search.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

