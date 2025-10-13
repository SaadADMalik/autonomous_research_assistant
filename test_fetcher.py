import asyncio
import aiohttp
import xml.etree.ElementTree as ET
import urllib.parse
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_arxiv(query: str, max_results: int = 5):
    logger.info(f"Testing Arxiv for query: {query}")
    
    # Try multiple query formats
    query_formats = [
        f"all:{query}",
        f"{query}",
        f"ti:{query}",
        f"abs:{query}",
        "cat:quant-ph"  # Fallback category
    ]
    
    for i, search_query in enumerate(query_formats):
        try:
            async with aiohttp.ClientSession() as session:
                query_encoded = urllib.parse.quote(search_query)
                url = f"http://export.arxiv.org/api/query?search_query={query_encoded}&max_results={max_results}"
                logger.debug(f"Attempt {i+1}: Arxiv API URL: {url}")
                
                async with session.get(url, timeout=10) as response:
                    logger.debug(f"Attempt {i+1}: Arxiv status: {response.status}")
                    response_text = await response.text()
                    
                    # Check for results
                    has_results = 'totalResults>0<' in response_text or '>0<' in response_text
                    if not has_results:
                        logger.debug(f"Attempt {i+1}: No results for '{search_query}'")
                        continue
                    
                    # Parse results
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    root = ET.fromstring(response_text)
                    results = []
                    
                    for entry in root.findall("atom:entry", ns):
                        title = entry.find("atom:title", ns)
                        summary = entry.find("atom:summary", ns)
                        url = entry.find("atom:id", ns)
                        published = entry.find("atom:published", ns)
                        
                        if title is None or summary is None or url is None or published is None:
                            logger.warning("Missing fields in Arxiv entry")
                            continue
                            
                        results.append({
                            "title": title.text.strip(),
                            "summary": summary.text.strip()[:200] + "...",  # Truncate for display
                            "url": url.text.strip(),
                            "year": int(published.text[:4])
                        })
                    
                    if results:
                        logger.info(f"Arxiv results using '{search_query}': {len(results)} documents")
                        return results
                        
        except Exception as e:
            logger.error(f"Attempt {i+1}: Arxiv error: {str(e)}")
            continue
    
    logger.warning("All ArXiv attempts failed")
    return []

async def test_wikipedia(query: str, max_results: int = 5):
    logger.info(f"Testing Wikipedia for query: {query}")
    try:
        headers = {
            'User-Agent': 'Autonomous Research Assistant/1.0 (educational project)'
        }
        
        async with aiohttp.ClientSession() as session:
            url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&srlimit={max_results}"
            logger.debug(f"Wikipedia API URL: {url}")
            
            async with session.get(url, headers=headers, timeout=10) as response:
                logger.debug(f"Wikipedia status: {response.status}")
                
                if response.status == 403:
                    logger.error("Wikipedia returned 403 - blocked request")
                    return []
                
                data = await response.json()
                logger.debug(f"Wikipedia response keys: {list(data.keys())}")
                
                results = [
                    {
                        "title": item["title"],
                        "summary": item.get("snippet", "").replace("<span>", "").replace("</span>", "")[:200] + "...",
                        "url": f"https://en.wikipedia.org/wiki/{item['title'].replace(' ', '_')}",
                        "year": 2025
                    }
                    for item in data.get("query", {}).get("search", [])
                ]
                logger.info(f"Wikipedia results: {len(results)} documents")
                return results
                
    except Exception as e:
        logger.error(f"Wikipedia error: {str(e)}")
        return []

async def main():
    query = "Quantum Computing"
    print(f"\n=== Testing ArXiv API ===")
    arxiv_results = await test_arxiv(query)
    if arxiv_results:
        print(f"✓ Found {len(arxiv_results)} ArXiv results:")
        for i, result in enumerate(arxiv_results[:2], 1):
            print(f"  {i}. {result['title'][:60]}...")
    else:
        print("✗ No ArXiv results found")
    
    print(f"\n=== Testing Wikipedia API ===")
    wikipedia_results = await test_wikipedia(query)
    if wikipedia_results:
        print(f"✓ Found {len(wikipedia_results)} Wikipedia results:")
        for i, result in enumerate(wikipedia_results[:2], 1):
            print(f"  {i}. {result['title'][:60]}...")
    else:
        print("✗ No Wikipedia results found")

if __name__ == "__main__":
    asyncio.run(main())