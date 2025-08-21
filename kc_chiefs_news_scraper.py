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

class KCChiefsNewsScraper:
    def __init__(self, lm_studio_url: str = "http://localhost:1234/v1/chat/completions", 
                 lm_studio_api_key: str = "lm-studio"):
        """
        Initialize the KC Chiefs news scraper
        
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
    
    def search_news_sources(self) -> List[Dict]:
        """Search multiple sources for KC Chiefs news"""
        news_stories = []
        
        # Define news sources and search patterns
        sources = [
            {
                'name': 'ESPN',
                'search_url': 'https://www.espn.com/search/_/q/kansas%20city%20chiefs',
                'base_url': 'https://www.espn.com'
            },
            {
                'name': 'NFL.com',
                'search_url': 'https://www.nfl.com/teams/kansas-city-chiefs/',
                'base_url': 'https://www.nfl.com'
            },
            {
                'name': 'Chiefs Official',
                'search_url': 'https://www.chiefs.com/news/',
                'base_url': 'https://www.chiefs.com'
            },
            {
                'name': 'Arrowhead Pride',
                'search_url': 'https://www.arrowheadpride.com/',
                'base_url': 'https://www.arrowheadpride.com'
            },
            {
                'name': 'Yahoo Sports',
                'search_url': 'https://sports.yahoo.com/nfl/teams/kansas-city-chiefs/',
                'base_url': 'https://sports.yahoo.com'
            },
            {
                'name': 'The Athletic',
                'search_url': 'https://theathletic.com/nfl/team/chiefs/',
                'base_url': 'https://theathletic.com'
            },
            {
                'name': 'Chiefs Digest',
                'search_url': 'https://www.chiefsdigest.com/',
                'base_url': 'https://www.chiefsdigest.com'
            },
            {
                'name': 'Chiefs Wire',
                'search_url': 'https://chiefswire.usatoday.com/',
                'base_url': 'https://chiefswire.usatoday.com'
            },
            {
                'name': 'Bleacher Report',
                'search_url': 'https://bleacherreport.com/kansas-city-chiefs',
                'base_url': 'https://bleacherreport.com'
            },
            {
                'name': 'Arrowhead Addict',
                'search_url': 'https://arrowheadaddict.com/',
                'base_url': 'https://arrowheadaddict.com'
            }
        ]
        
        for source in sources:
            try:
                stories = self._scrape_source(source)
                news_stories.extend(stories)
                time.sleep(1)  # Be respectful to servers
            except Exception as e:
                logger.error(f"Error scraping {source['name']}: {e}")
                
        return news_stories
    
    def _scrape_source(self, source: Dict) -> List[Dict]:
        """Scrape a specific news source"""
        stories = []
        
        try:
            response = self.session.get(source['search_url'], timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Site-specific selectors for better extraction
            site_selectors = {
                'Arrowhead Pride': ['article h2 a', 'h3 a', '.c-entry-box--compact__title a'],
                'Yahoo Sports': ['.Fw-b a', '.article-wrap h3 a', '.Fz-14 a'],
                'The Athletic': ['[data-testid="article-title"] a', 'article h3 a', '.f-article-title a'],
                'Chiefs Digest': ['article h2 a', '.post-title a', 'h3 a'],
                'Chiefs Wire': ['.c-entry-box--compact__title a', 'h3 a', 'article h2 a'],
                'Bleacher Report': ['.articleTitle a', 'h3 a', '.atom-text a'],
                'Arrowhead Addict': ['article h2 a', '.entry-title a', 'h3 a'],
                'ESPN': ['.contentItem__title a', 'h3 a', '.Card__Title a'],
                'NFL.com': ['.d3-o-media-object__title a', 'h3 a', '.nfl-c-custom-promo__title a'],
                'Chiefs Official': ['.nfl-c-custom-promo__title a', 'h3 a', 'article h2 a']
            }
            
            # Try site-specific selectors first
            links = []
            if source['name'] in site_selectors:
                for selector in site_selectors[source['name']]:
                    found_links = soup.select(selector)
                    if found_links:
                        links.extend(found_links)
                        break
            
            # Fallback to generic selectors if site-specific didn't work
            if not links:
                generic_selectors = [
                    'article h2 a', 'article h3 a', '.entry-title a', 
                    '.post-title a', '.article-title a', 'h2 a', 'h3 a'
                ]
                for selector in generic_selectors:
                    found_links = soup.select(selector)
                    if found_links:
                        links.extend(found_links)
                        break
            
            # Final fallback: all links
            if not links:
                links = soup.find_all('a', href=True)
            
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
                
                # Filter for relevant Chiefs content
                if self._is_chiefs_related(title, href):
                    full_url = urljoin(source['base_url'], href)
                    
                    # Avoid duplicates
                    if any(story['url'] == full_url for story in stories):
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
            
        logger.info(f"Found {len(stories)} stories from {source['name']}")
        return stories
    
    def _is_chiefs_related(self, title: str, url: str) -> bool:
        """Check if content is related to Kansas City Chiefs"""
        chiefs_keywords = ['chiefs', 'kansas city', 'kc', 'mahomes', 'arrowhead', 'nfl']
        text_to_check = f"{title.lower()} {url.lower()}"
        
        return any(keyword in text_to_check for keyword in chiefs_keywords) and len(title) > 10
    
    def _extract_metadata(self, link_element, soup) -> Dict:
        """Extract additional metadata like publish date, engagement metrics"""
        metadata = {}
        
        # Try to find publish date
        parent = link_element.parent
        if parent:
            date_patterns = [
                r'\d{1,2}/\d{1,2}/\d{4}',
                r'\d{4}-\d{2}-\d{2}',
                r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}'
            ]
            
            parent_text = parent.get_text()
            for pattern in date_patterns:
                match = re.search(pattern, parent_text)
                if match:
                    metadata['publish_date'] = match.group()
                    break
        
        return metadata
    
    def save_links_to_file(self, stories: List[Dict], filename: str = "chiefs_news_links.json"):
        """Save all found news links to a file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(stories, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(stories)} news stories to {filename}")
    
    def select_best_story(self, stories: List[Dict]) -> Optional[Dict]:
        """Use LM Studio to select the best story based on viral potential"""
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
        Pick the best Kansas City Chiefs story for a viral YouTube video. Just respond with the NUMBER only.
        
        Consider: Key players, breaking news, impactful injuries, controversy, playoff impact, Emotional Arousal, Narrative and Human Connection, Timeliness.
        Stories:
        {chr(10).join(stories_text)}
        
        Answer with just the number (example: 5):
        """
        
        try:
            selection = self._query_lm_studio(prompt)
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
        
        # Simple scoring based on keywords and source priority
        viral_keywords = [
            'mahomes', 'patrick mahomes', 'travis kelce', 'kelce',
            'playoff', 'super bowl', 'trade', 'injury', 'contract',
            'breaking', 'suspended', 'fined', 'record', 'mvp',
            'chiefs kingdom', 'arrowhead', 'andy reid'
        ]
        
        source_priority = {
            'ESPN': 10, 'NFL.com': 9, 'The Athletic': 8, 'Yahoo Sports': 7,
            'Chiefs Official': 9, 'Arrowhead Pride': 6, 'Chiefs Wire': 5,
            'Bleacher Report': 4, 'Chiefs Digest': 3, 'Arrowhead Addict': 2
        }
        
        scored_stories = []
        for story in stories:
            score = 0
            title_lower = story['title'].lower()
            
            # Keyword scoring
            for keyword in viral_keywords:
                if keyword in title_lower:
                    score += 3
            
            # Source priority scoring
            score += source_priority.get(story['source'], 1)
            
            # Length preference (not too short, not too long)
            title_len = len(story['title'])
            if 40 <= title_len <= 100:
                score += 2
            
            scored_stories.append((story, score))
        
        # Sort by score and return the best
        scored_stories.sort(key=lambda x: x[1], reverse=True)
        best_story = scored_stories[0][0]
        
        logger.info(f"📊 Fallback selected story: {best_story['title']} (Score: {scored_stories[0][1]})")
        return best_story
    
    def scrape_full_article(self, story_url: str) -> str:
        """Scrape the full content of an article"""
        try:
            response = self.session.get(story_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "aside", ".ad", ".advertisement"]):
                element.decompose()
            
            # Try to find article content using common selectors
            content_selectors = [
                # Site-specific selectors
                '.c-entry-content',  # SB Nation sites like Arrowhead Pride
                '.caas-body',        # Yahoo Sports
                '[data-module="ArticleBody"]',  # The Athletic
                '.article-content',  # Generic article content
                '.entry-content',    # WordPress sites
                '.post-content',     # Blog sites
                '.story-body',       # News sites
                '.article-body',     # News sites
                '.content-body',     # Various sites
                # Generic selectors
                'article',
                '.content',
                'main',
                '[class*="article"]',
                '[class*="story"]',
                '[class*="post-content"]'
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
                        # Filter out very short snippets and common boilerplate
                        if (len(text) > 20 and 
                            not any(skip_phrase in text.lower() for skip_phrase in 
                                   ['subscribe', 'follow us', 'related:', 'more:', 'advertisement', 'share this'])):
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
                    if len(text) > 30:  # Only substantial paragraphs
                        meaningful_paragraphs.append(text)
                
                content = ' '.join(meaningful_paragraphs[:15])  # Limit number of paragraphs
            
            # Clean up the content
            content = re.sub(r'\s+', ' ', content)  # Replace multiple whitespace with single space
            content = content[:5000]  # Increased content limit for richer context
            
            return content
            
        except Exception as e:
            logger.error(f"Error scraping article content from {story_url}: {e}")
            return ""
    
    def rewrite_as_video_script(self, story: Dict, article_content: str) -> str:
        """Use LM Studio to rewrite the story as an engaging video script"""
        
        # Check if LM Studio is available
        if not self.lm_studio_available:
            logger.warning("LM Studio not available, creating basic script template...")
            return self._create_basic_script(story, article_content)
        
        prompt = f"""
        Write a detailed YouTube video script for Chiefs fans. Make it engaging and comprehensive.
        
        STORY TITLE: {story['title']}
        SOURCE: {story['source']}
        
        FULL ARTICLE CONTENT:
        {article_content[:3000] if article_content else "No additional content available."}
        
        Create a 4-6 minute video script (600-900 words) with these sections:
        
        HOOK (0-15 seconds): Grab attention immediately
        MAIN CONTENT (15 seconds - 4 minutes): Explain the news in detail with context
        ANALYSIS (4-5 minutes): What this means for Chiefs Kingdom
        CALL TO ACTION (5-6 minutes): Engage viewers
        
        Requirements:
        - Be enthusiastic and conversational
        - Include [visual cue suggestions in brackets]
        - Add personal commentary and opinions
        - Make it feel like talking to a friend about Chiefs news
        - Use specific details from the article content
        - Build excitement and engagement throughout
        
        Write the complete script:
        """
        
        try:
            script = self._query_lm_studio(prompt)
            logger.info("✅ AI-generated video script created successfully!")
            return script
        except Exception as e:
            logger.error(f"Error generating AI script, using template: {e}")
            return self._create_basic_script(story, article_content)
    
    def _create_basic_script(self, story: Dict, article_content: str) -> str:
        """Create a basic video script template when AI isn't available"""
        
        script = f"""
# CHIEFS KINGDOM VIDEO SCRIPT
## Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**TITLE:** {story['title']}
**SOURCE:** {story['source']}

---

## HOOK (0-10 seconds)
[Show Chiefs logo/recent highlight footage]

What's up Chiefs Kingdom! I've got some breaking news that you NEED to know about. 
This could change everything we thought we knew about our team!

[Pause for dramatic effect]

## MAIN CONTENT (90 seconds - 2 minutes)
[Show relevant images/footage throughout]

So here's what's happening with our Kansas City Chiefs...

{article_content[:800] if article_content else "The story involves important developments for the Chiefs organization that fans will want to know about."}

[Show relevant stats/graphics]

## ANALYSIS & OPINION (2-2.5 minutes)
Now, here's what I think this means for Chiefs Kingdom:

- This could impact our playoff chances
- Fans should be paying close attention to this development
- It's another example of why this organization is special

[Show fan reactions/social media]

## CALL TO ACTION (2.5-3 minutes)
What do YOU think about this news, Chiefs Kingdom? 

Drop your thoughts in the comments below - I read every single one!

If this video helped keep you updated on the latest Chiefs news, smash that like button and hit subscribe for more Chiefs content!

[Show subscribe button animation]

And don't forget to ring that notification bell so you never miss breaking Chiefs news!

Until next time, Chiefs Kingdom - Let's Go Chiefs!

[End with Chiefs highlight reel]

---

**VIDEO LENGTH:** Approximately 4 minutes
**ENGAGEMENT ELEMENTS:** Question for comments, like/subscribe reminders
**VISUAL CUES:** Included throughout in [brackets]
"""
        
        logger.info("📝 Basic script template created")
        return script
    
    def _query_lm_studio(self, prompt: str, max_tokens: int = 1200) -> str:
        """Query the LM Studio local LLM"""
        payload = {
            "model": "local-model",  # LM Studio uses this as default
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that gives direct, detailed answers for content creation."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.4,  # Slightly higher for more creativity
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.lm_studio_api_key}"
        }
        
        # Increased timeout for slower PCs and longer content
        for attempt in range(2):
            try:
                logger.info(f"Querying LM Studio (attempt {attempt + 1}/2)...")
                response = requests.post(self.lm_studio_url, json=payload, headers=headers, timeout=120)  # 2 minutes
                response.raise_for_status()
                
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                if content.strip():  # Make sure we got actual content
                    logger.info(f"Received response: {len(content)} characters")
                    return content
                else:
                    logger.warning("Empty response from LM Studio, retrying...")
                    continue
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timed out on attempt {attempt + 1} (this is normal for slower PCs)")
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
    
    def save_script_to_file(self, script: str, filename: str = "chiefs_video_script.txt"):
        """Save the generated video script to a file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_with_timestamp = f"{timestamp}_{filename}"
        
        with open(filename_with_timestamp, 'w', encoding='utf-8') as f:
            f.write(script)
        
        logger.info(f"Saved video script to {filename_with_timestamp}")
        return filename_with_timestamp

def main():
    """Main execution function"""
    # Initialize the scraper
    scraper = KCChiefsNewsScraper()
    
    try:
        # Step 1: Search for KC Chiefs news
        logger.info("Searching for KC Chiefs news stories...")
        news_stories = scraper.search_news_sources()
        
        if not news_stories:
            logger.warning("No news stories found!")
            return
        
        # Step 2: Save links to file
        logger.info("Saving news links to file...")
        scraper.save_links_to_file(news_stories)
        
        # Step 3: Select best story using AI
        logger.info("Selecting best story for video content...")
        best_story = scraper.select_best_story(news_stories)
        
        if not best_story:
            logger.warning("Could not select best story!")
            return
        
        # Step 4: Scrape full article content
        logger.info(f"Scraping full content for: {best_story['title']}")
        article_content = scraper.scrape_full_article(best_story['url'])
        
        # Step 5: Generate video script
        logger.info("Generating video script...")
        video_script = scraper.rewrite_as_video_script(best_story, article_content)
        
        # Step 6: Save script to file
        script_filename = scraper.save_script_to_file(video_script)
        
        logger.info("Process completed successfully!")
        logger.info(f"Links saved to: chiefs_news_links.json")
        logger.info(f"Video script saved to: {script_filename}")
        
    except Exception as e:
        logger.error(f"Error in main process: {e}")

if __name__ == "__main__":
    main()
