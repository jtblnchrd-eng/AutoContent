import requests
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from typing import List, Dict, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TrumpNewsBlogGenerator:
    def __init__(self, lm_studio_url: str = "http://localhost:1234/v1/chat/completions", 
                 lm_studio_api_key: str = "lm-studio"):
        """
        Initialize the Trump administration news blog generator
        
        Args:
            lm_studio_url: URL for your LM Studio API endpoint
            lm_studio_api_key: API key for LM Studio (default works for local instance)
        """
        self.lm_studio_url = lm_studio_url
        self.lm_studio_api_key = lm_studio_api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.lm_studio_available = self._check_lm_studio_connection()
        
    def _check_lm_studio_connection(self) -> bool:
        """Check if LM Studio is running and accessible"""
        try:
            # Try to connect to LM Studio
            test_url = self.lm_studio_url.replace('/v1/chat/completions', '/v1/models')
            response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                logger.info("✅ LM Studio connection successful!")
                return True
            else:
                logger.warning(f"⚠️ LM Studio responded with status {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.error("❌ LM Studio not accessible. Please check:")
            logger.error("   1. LM Studio is running")
            logger.error("   2. Local Server is started in LM Studio")
            logger.error("   3. Server is running on localhost:1234")
            logger.error("   4. A model is loaded")
            return False
        except Exception as e:
            logger.error(f"❌ Error connecting to LM Studio: {e}")
            return False

    def search_trump_news_sources(self) -> List[Dict]:
        """Search multiple sources for Trump administration news"""
        news_stories = []
        
        # Define news sources - using category pages and RSS-like feeds for better success
        sources = [
            {
                'name': 'CNN Politics',
                'search_url': 'https://www.cnn.com/politics',
                'base_url': 'https://www.cnn.com'
            },
            {
                'name': 'Fox News Politics',
                'search_url': 'https://www.foxnews.com/politics',
                'base_url': 'https://www.foxnews.com'
            },
            {
                'name': 'Politico',
                'search_url': 'https://www.politico.com/news/politics',
                'base_url': 'https://www.politico.com'
            },
            {
                'name': 'Reuters Politics',
                'search_url': 'https://www.reuters.com/world/us/',
                'base_url': 'https://www.reuters.com'
            },
            {
                'name': 'Associated Press',
                'search_url': 'https://apnews.com/hub/politics',
                'base_url': 'https://apnews.com'
            },
            {
                'name': 'The Hill',
                'search_url': 'https://thehill.com/news/',
                'base_url': 'https://thehill.com'
            },
            {
                'name': 'Washington Post Politics',
                'search_url': 'https://www.washingtonpost.com/politics/',
                'base_url': 'https://www.washingtonpost.com'
            },
            {
                'name': 'NBC News Politics',
                'search_url': 'https://www.nbcnews.com/politics',
                'base_url': 'https://www.nbcnews.com'
            },
            {
                'name': 'ABC News Politics',
                'search_url': 'https://abcnews.go.com/Politics',
                'base_url': 'https://abcnews.go.com'
            },
            {
                'name': 'Yahoo News',
                'search_url': 'https://news.yahoo.com/politics/',
                'base_url': 'https://news.yahoo.com'
            }
        ]
        
        for source in sources:
            try:
                stories = self._scrape_source(source)
                news_stories.extend(stories)
                time.sleep(3)  # More respectful delay for news sites
            except Exception as e:
                logger.error(f"Error scraping {source['name']}: {e}")
                
        return news_stories
    
    def _scrape_source(self, source: Dict) -> List[Dict]:
        """Scrape a specific news source for Trump-related content"""
        stories = []
        
        try:
            # Add more realistic headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(source['search_url'], headers=headers, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Updated site-specific selectors based on current website structures
            site_selectors = {
                'CNN Politics': [
                    'h3.cd__headline a', 'h3 a[data-link-type="article"]', 
                    '.container__headline-text a', 'article h3 a', 
                    '.cd__content a', 'a[data-link-type]'
                ],

                'Politico': [
                    'h3 a', '.headline a', '.story-frag__link', 
                    'article h3 a', '.summary a', 'h2 a'
                ],
                'Reuters Politics': [
                    '[data-testid="Heading"] a', 'h3 a', '.story-title a',
                    'article h3 a', '.media-story-card__headline a'
                ],
                'Associated Press': [
                    '.Page-content h2 a', '.CardHeadline a', 'h1 a', 
                    'h2 a', 'h3 a', '.Component-headline a'
                ],
                'The Hill': [
                    '.node__title a', 'h2 a', 'h3 a', '.field--name-title a',
                    'article h2 a', '.news-item h3 a'
                ],
                'Washington Post Politics': [
                    '.headline a', 'h3 a', '.pb-feature-headline a',
                    'article h3 a', '.story-headline a'
                ],
                'NBC News Politics': [
                    '.teaserCard__headline a', 'h2 a', 'h3 a',
                    'article h3 a', '.story-body h2 a'
                ],
                'ABC News Politics': [
                    '.News__Item__Headline a', 'h2 a', 'h3 a',
                    'article h2 a', '.ContentRoll__Headline a'
                ],
                'Yahoo News': [
                    '.Fw-b a', '.Fz-14 a', 'h3 a', 'article h3 a',
                    '.stream-item-title a'
                ]
            }
            
            # Try multiple approaches to find links
            links = []
            
            # 1. Try site-specific selectors
            if source['name'] in site_selectors:
                for selector in site_selectors[source['name']]:
                    try:
                        found_links = soup.select(selector)
                        if found_links:
                            links.extend(found_links)
                            logger.info(f"Found {len(found_links)} links with selector: {selector}")
                    except Exception as e:
                        continue
            
            # 2. Generic news article selectors
            if len(links) < 5:
                generic_selectors = [
                    'article h2 a', 'article h3 a', 'article h1 a',
                    '.headline a', '.title a', '.story-title a',
                    'h2 a[href*="/"]', 'h3 a[href*="/"]',
                    'a[href*="/politics"]', 'a[href*="/news"]',
                    '.story a', '.article a'
                ]
                for selector in generic_selectors:
                    try:
                        found_links = soup.select(selector)
                        if found_links:
                            links.extend(found_links)
                            break
                    except Exception as e:
                        continue
            
            # 3. Final fallback - all links but filter more carefully
            if len(links) < 3:
                all_links = soup.find_all('a', href=True)
                # Filter for likely article links
                for link in all_links:
                    href = link.get('href', '')
                    if any(pattern in href.lower() for pattern in ['/politics', '/news', '/article', '/story', '2025', '2024']):
                        links.append(link)
            
            logger.info(f"Total links found for {source['name']}: {len(links)}")
            
            # Process found links
            processed_count = 0
            for link in links:
                if processed_count >= 15:  # Limit per source
                    break
                    
                href = link.get('href')
                title = link.get_text(strip=True)
                
                # Skip if no meaningful title or href
                if not title or not href or len(title) < 15:
                    continue
                
                # Skip navigation links, ads, etc.
                skip_patterns = ['#', 'javascript:', 'mailto:', '/video/', '/photo/', '/gallery/']
                if any(pattern in href.lower() for pattern in skip_patterns):
                    continue
                
                # Filter for relevant Trump/political content
                if self._is_trump_related(title, href):
                    full_url = urljoin(source['base_url'], href)
                    
                    # Avoid duplicates
                    if any(story['url'] == full_url for story in stories):
                        continue
                    
                    # Validate URL
                    if not self._is_valid_url(full_url):
                        continue
                    
                    story = {
                        'title': title,
                        'url': full_url,
                        'source': source['name'],
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    # Try to extract additional metadata
                    story.update(self._extract_metadata(link, soup))
                    stories.append(story)
                    processed_count += 1
                    
        except Exception as e:
            logger.error(f"Error scraping {source['name']}: {e}")
            
        logger.info(f"Successfully found {len(stories)} relevant stories from {source['name']}")
        return stories
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and not a fragment or relative path"""
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc and parsed.scheme in ['http', 'https'])
        except:
            return False
    
    def _is_trump_related(self, title: str, url: str) -> bool:
        """Check if content is related to Trump administration or current politics"""
        # Expanded keywords for broader political coverage since Trump is president again
        political_keywords = [
            'trump', 'donald trump', 'president', 'white house', 'administration', 
            'cabinet', 'executive', 'federal', 'government', 'policy', 'politics',
            'republican', 'gop', 'congress', 'senate', 'house', 'washington',
            'election', 'campaign', 'political', 'nominee', 'appointment',
            'bill', 'legislation', 'vote', 'debate', 'hearing', 'investigation'
        ]
        
        # Current administration figures and key topics
        current_figures = [
            'vance', 'pence', 'desantis', 'ramaswamy', 'noem', 'rubio',
            'hegseth', 'gaetz', 'kennedy', 'musk', 'vivek'
        ]
        
        text_to_check = f"{title.lower()} {url.lower()}"
        
        # Check for political relevance
        has_political_content = any(keyword in text_to_check for keyword in political_keywords)
        has_current_figures = any(figure in text_to_check for figure in current_figures)
        
        # Must be political and substantial
        is_substantial = len(title) > 15
        
        # Exclude certain non-article content
        exclude_patterns = ['video', 'gallery', 'photo', 'subscribe', 'newsletter', 'weather', 'sports']
        is_excluded = any(pattern in text_to_check for pattern in exclude_patterns)
        
        return (has_political_content or has_current_figures) and is_substantial and not is_excluded
    
    def _extract_metadata(self, link_element, soup) -> Dict:
        """Extract additional metadata like publish date"""
        metadata = {}
        
        # Try to find publish date
        parent = link_element.parent
        if parent:
            date_patterns = [
                r'\d{1,2}/\d{1,2}/\d{4}',
                r'\d{4}-\d{2}-\d{2}',
                r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}',
                r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}'
            ]
            
            parent_text = parent.get_text()
            for pattern in date_patterns:
                match = re.search(pattern, parent_text, re.IGNORECASE)
                if match:
                    metadata['publish_date'] = match.group()
                    break
        
        return metadata
    
    def save_links_to_file(self, stories: List[Dict], filename: str = "trump_news_links.json"):
        """Save all found news links to a file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(stories, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(stories)} news stories to {filename}")
    
    def select_best_story(self, stories: List[Dict]) -> Optional[Dict]:
        """Use LM Studio to select the best story for blog content"""
        if not stories:
            return None
        
        # Check if LM Studio is available
        if not self.lm_studio_available:
            logger.warning("LM Studio not available, using fallback selection...")
            return self._fallback_story_selection(stories)
            
        # Prepare stories for LLM evaluation
        stories_text = []
        for i, story in enumerate(stories):
            stories_text.append(f"{i+1}. {story['title']} (Source: {story['source']})")
        
        prompt = f"""
        Pick the best Trump administration story for a detailed blog article. Just respond with the NUMBER only.
        
        Consider: breaking news, policy impact, controversy, public interest, analytical potential, current relevance.
        
        Stories:
        {chr(10).join(stories_text)}
        
        Answer with just the number (example: 3):
        """
        
        try:
            selection = self._query_lm_studio(prompt, max_tokens=50)
            # Extract number from response
            import re
            numbers = re.findall(r'\d+', selection)
            if numbers:
                selected_index = int(numbers[0]) - 1
                if 0 <= selected_index < len(stories):
                    logger.info(f"✅ AI selected story: {stories[selected_index]['title']}")
                    return stories[selected_index]
        except Exception as e:
            logger.error(f"Error with AI selection, using fallback: {e}")
            return self._fallback_story_selection(stories)
        
        # Fallback: return first story
        return stories[0] if stories else None
    
    def _fallback_story_selection(self, stories: List[Dict]) -> Optional[Dict]:
        """Fallback story selection when LM Studio isn't available"""
        if not stories:
            return None
        
        # Simple scoring for political content
        important_keywords = [
            'breaking', 'exclusive', 'investigation', 'scandal', 'policy',
            'executive order', 'cabinet', 'congress', 'senate', 'house',
            'impeach', 'controversy', 'decision', 'announcement', 'statement'
        ]
        
        source_priority = {
            'Reuters Politics': 10, 'Associated Press': 10, 'CNN Politics': 9,
            'Washington Post': 9, 'New York Times': 9, 'Politico': 8,
            'NBC News': 7, 'ABC News': 7, 'Fox News Politics': 6, 'The Hill': 5
        }
        
        scored_stories = []
        for story in stories:
            score = 0
            title_lower = story['title'].lower()
            
            # Keyword scoring
            for keyword in important_keywords:
                if keyword in title_lower:
                    score += 3
            
            # Source priority scoring
            score += source_priority.get(story['source'], 1)
            
            # Recent content preference
            if 'today' in title_lower or '2025' in story.get('publish_date', ''):
                score += 5
            
            scored_stories.append((story, score))
        
        # Sort by score and return the best
        scored_stories.sort(key=lambda x: x[1], reverse=True)
        best_story = scored_stories[0][0]
        
        logger.info(f"📊 Fallback selected story: {best_story['title']} (Score: {scored_stories[0][1]})")
        return best_story
    
    def scrape_full_article(self, story_url: str) -> str:
        """Scrape the full content of a news article"""
        try:
            response = self.session.get(story_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "aside", ".ad", ".advertisement", ".social-share"]):
                element.decompose()
            
            # Try to find article content using news-specific selectors
            content_selectors = [
                # News site specific selectors
                '.article-body',           # Many news sites
                '.story-body',            # BBC, others
                '.entry-content',         # WordPress news sites
                '.post-content',          # Blog-style news
                '.article-content',       # General news
                '[data-module="ArticleBody"]',  # Some news sites
                '.field-body',            # Some CMS sites
                '.content-body',          # Various sites
                '.article__body',         # News sites
                '.story__body',           # Story format sites
                # Generic selectors
                'article',
                '.content',
                'main',
                '[class*="article"]',
                '[class*="story"]'
            ]
            
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    # Get text from paragraphs within the content area
                    paragraphs = elements[0].find_all(['p', 'div'], recursive=True)
                    paragraph_texts = []
                    
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        # Filter out short snippets and common boilerplate
                        skip_phrases = [
                            'subscribe', 'follow us', 'related:', 'more:', 'advertisement', 
                            'share this', 'sign up', 'newsletter', 'breaking news alert',
                            'watch:', 'read more', 'continue reading', 'click here'
                        ]
                        if (len(text) > 25 and 
                            not any(skip_phrase in text.lower() for skip_phrase in skip_phrases)):
                            paragraph_texts.append(text)
                    
                    if paragraph_texts:
                        content = ' '.join(paragraph_texts)
                        break
            
            # Fallback: get all meaningful paragraph text
            if not content:
                paragraphs = soup.find_all('p')
                meaningful_paragraphs = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 40:  # Only substantial paragraphs
                        meaningful_paragraphs.append(text)
                
                content = ' '.join(meaningful_paragraphs[:20])  # Limit number of paragraphs
            
            # Clean up the content
            content = re.sub(r'\s+', ' ', content)  # Replace multiple whitespace with single space
            content = content[:6000]  # Limit content length for LLM processing
            
            return content
            
        except Exception as e:
            logger.error(f"Error scraping article content from {story_url}: {e}")
            return ""
    
    def generate_blog_article(self, story: Dict, article_content: str) -> str:
        """Use LM Studio to generate a comprehensive blog article"""
        
        # Check if LM Studio is available
        if not self.lm_studio_available:
            logger.warning("LM Studio not available, creating basic blog template...")
            return self._create_basic_blog(story, article_content)
        
        prompt = f"""
        Write a comprehensive blog article based on this Trump administration news story. 
        Create original, analytical content that goes beyond just reporting the facts.
        
        ORIGINAL STORY TITLE: {story['title']}
        SOURCE: {story['source']}
        
        ARTICLE CONTENT TO ANALYZE:
        {article_content[:4000] if article_content else "No additional content available."}
        
        Write a 1000-1500 word blog article with these requirements:
        
        1. COMPELLING HEADLINE: Create an engaging title (different from the original)
        2. INTRODUCTION: Hook readers and provide context
        3. MAIN ANALYSIS: Break down the key points and implications
        4. POLITICAL CONTEXT: Explain how this fits into broader political trends
        5. IMPACT ASSESSMENT: What this means for various stakeholders
        6. CONCLUSION: Thoughtful wrap-up with key takeaways
        
        Writing style:
        - Analytical and insightful, not just reporting
        - Balanced perspective considering multiple viewpoints
        - Professional tone suitable for political blog
        - Use specific details from the source material
        - Include relevant background context
        - Make complex political issues accessible
        
        Format as a complete blog post with clear sections.
        """
        
        try:
            blog_article = self._query_lm_studio(prompt, max_tokens=1500)
            logger.info("✅ AI-generated blog article created successfully!")
            return blog_article
        except Exception as e:
            logger.error(f"Error generating AI blog article, using template: {e}")
            return self._create_basic_blog(story, article_content)
    
    def _create_basic_blog(self, story: Dict, article_content: str) -> str:
        """Create a basic blog article template when AI isn't available"""
        
        blog_template = f"""
# TRUMP ADMINISTRATION NEWS ANALYSIS
## Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

### {story['title']}

**Source:** {story['source']}  
**Analysis Date:** {datetime.now().strftime("%B %d, %Y")}

---

## Executive Summary

This analysis examines recent developments in the Trump administration based on reporting from {story['source']}. The following article provides context and implications for current political developments.

## Key Developments

{article_content[:1500] if article_content else "Full details are available in the original reporting."}

## Political Context

This development occurs within the broader context of ongoing political dynamics in Washington. Key stakeholders and affected parties should monitor how this situation evolves.

## Implications and Analysis

### Short-term Impact
- Immediate effects on policy implementation
- Response from political allies and opponents
- Media and public reaction

### Long-term Considerations
- Potential lasting effects on administration priorities
- Impact on upcoming political cycles
- Broader implications for governance

## Conclusion

This situation represents another significant development in the current political landscape. Continued monitoring of related developments will be important for understanding the full scope of implications.

---

*This analysis is based on publicly available reporting. Readers are encouraged to consult multiple sources for comprehensive understanding of political developments.*

**Word Count:** Approximately 800-1000 words  
**Reading Time:** 4-5 minutes
"""
        
        logger.info("📝 Basic blog template created")
        return blog_template
    
    def _query_lm_studio(self, prompt: str, max_tokens: int = 1200) -> str:
        """Query the LM Studio local LLM"""
        payload = {
            "model": "local-model",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a skilled political analyst and blogger who writes insightful, balanced articles about current events and government affairs."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.5,  # Balanced creativity and accuracy
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.lm_studio_api_key}"
        }
        
        # Increased timeout for thorough blog generation
        for attempt in range(2):
            try:
                logger.info(f"Generating content with LM Studio (attempt {attempt + 1}/2)...")
                response = requests.post(self.lm_studio_url, json=payload, headers=headers, timeout=150)  # 2.5 minutes
                response.raise_for_status()
                
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                if content.strip():
                    logger.info(f"Generated content: {len(content)} characters")
                    return content
                else:
                    logger.warning("Empty response from LM Studio, retrying...")
                    continue
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timed out on attempt {attempt + 1} (normal for detailed content generation)")
                if attempt == 0:
                    logger.info("Trying again...")
                    continue
                else:
                    raise
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"Error on attempt {attempt + 1}: {e}")
                    continue
                else:
                    raise
        
        raise Exception("Failed to get response after 2 attempts")
    
    def save_blog_to_file(self, blog_content: str, story_title: str) -> str:
        """Save the generated blog article to a file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Create a clean filename from the story title
        clean_title = re.sub(r'[^\w\s-]', '', story_title).strip()[:50]
        clean_title = re.sub(r'[-\s]+', '_', clean_title)
        filename = f"{timestamp}_{clean_title}_blog.md"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(blog_content)
        
        logger.info(f"Saved blog article to {filename}")
        return filename

def main():
    """Main execution function"""
    # Initialize the blog generator
    generator = TrumpNewsBlogGenerator()
    
    try:
        # Step 1: Search for Trump administration news
        logger.info("Searching for Trump administration news stories...")
        news_stories = generator.search_trump_news_sources()
        
        if not news_stories:
            logger.warning("No news stories found!")
            return
        
        # Step 2: Save links to file
        logger.info("Saving news links to file...")
        generator.save_links_to_file(news_stories)
        
        # Step 3: Select best story using AI or fallback
        logger.info("Selecting best story for blog content...")
        best_story = generator.select_best_story(news_stories)
        
        if not best_story:
            logger.warning("Could not select best story!")
            return
        
        # Step 4: Scrape full article content
        logger.info(f"Scraping full content for: {best_story['title']}")
        article_content = generator.scrape_full_article(best_story['url'])
        
        # Step 5: Generate blog article
        logger.info("Generating blog article...")
        blog_article = generator.generate_blog_article(best_story, article_content)
        
        # Step 6: Save blog to file
        blog_filename = generator.save_blog_to_file(blog_article, best_story['title'])
        
        logger.info("Process completed successfully!")
        logger.info(f"Links saved to: trump_news_links.json")
        logger.info(f"Blog article saved to: {blog_filename}")
        
    except Exception as e:
        logger.error(f"Error in main process: {e}")

if __name__ == "__main__":
    main()
