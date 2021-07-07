import re
import nltk
# RegexpTokenizer for splitting tokenizer based off specd regexp pattern
from nltk.tokenize import RegexpTokenizer
# parses url text into a useable URL object
from urllib.parse import urlparse
# ConfigParser reads info from config file
from configparser import ConfigParser
# our lovely webscraper that creates an object based on HTML text
from bs4 import BeautifulSoup
from collections import defaultdict, OrderedDict
# downloads a dependency thats needed for nltk to run
nltk.download('punkt')

'''
crawler meat:
Your task is to:
    1. parse the Web response
    2. extract enough information from the page (if it's a valid page) so to be able to answer the questions for the report
    3. return the list of URLs "scrapped" from that page. 


questions to answer:

1. How many unique pages did you find? Uniqueness for the purposes of this assignment is ONLY established by the URL, but discarding the fragment part. 
    So, for example, http://www.ics.uci.edu#aaa and http://www.ics.uci.edu#bbb are the same URL. Even if you implement additional methods for textual 
    similarity detection, please keep considering the above definition of unique pages for the purposes of counting the unique pages in this assignment.
        - solution: discard anything after the # and store in a global set, get length of set at end
        
2. What is the longest page in terms of the number of words? (HTML markup doesn’t count as words)
        - solution: use nltk to tokenize the webpage (picked this library for efficiency) and the filter out all non alnum words.
                    then compare word count with that of previous webpages to determine which webpage is the longest

3. What are the 50 most common words in the entire set of pages crawled under these domains? (Ignore English stop words, which can be found, for example, 
    here (Links to an external site.)) Submit the list of common words ordered by frequency.
        - solution: 

4. How many subdomains did you find in the ics.uci.edu domain? Submit the list of subdomains ordered alphabetically and the number of unique pages 
    detected in each subdomain. The content of this list should be lines containing URL, number, for example:
    http://vision.ics.uci.edu, 10 (not the actual number here)
        - solution: regex check to see if there is any part before ics.uci.edu, retrieve just that part (subdomain) and add to a dict
                    dict will have {url : unique_url_set} (eg. {'vision.ics.uci.edu' : (vision.ics.uci.edu/hello/my?name, ...)})
                    then add the defragmented url to the corresponding set
                    in the end return the domain and len(unique_url_set)

Some important notes:
1. Make sure to return only URLs that are within the domains and paths mentioned above! (see is_valid function in scraper.py -- you need to change it)
2. Make sure to defragment the URLs, i.e. remove the fragment part.
3. You can use whatever libraries make your life easier to parse things. Optional dependencies you might want to look at: BeautifulSoup, lxml (nudge, nudge, wink, wink!)
4. Optionally, in the scraper function, you can also save the URL and the web page on your local disk.
'''

'''
GLOBAL VARIABLES TO ANSWER QUESTIONS
'''
# unique_urls will contain all unique pages to answer question 1
unique_urls = set()
# subdomains will contain key: subdomain, value: set(unique_urls) to answer question 4
subdomains = defaultdict(set)
# url and word count of webpage with the most words -> with placeholders
longest_page = ("www", float("-inf"))
# dictionary to count word frequency
word_count = defaultdict(int)
# read stopword.txt into a set
stop_words = set()
with open('stop_words.txt') as f:
    for line in f:
        stop_words.add(line.strip())



# reading all acceptable domains from config file
config = ConfigParser()
config.read('config.ini')
# gets the domain part of the url
valid_domains = config['CRAWLER']['SEEDURL'].split(',')

def scraper(url, resp):
    # lets the function use global variable (python complained when this wasnt here)
    global longest_page
    # resp.raw_response.content gives HTML content, which we can pass to BeautifulSoup(content, 'lxml')
    # then to get all text on the page, use soup.get_text() -> answer the different qs/do stuff with it
    # then call extract_next_links() to get all links on this page -> we can validate the links with is_valid()

    # dictionary to keep track of output file writes, we will use subdomains dict for #4 output and longest_page tuple for #2 output
    # ordered dict preserves order of insertion
    output = OrderedDict()
    output['WEBPAGE AND RESPONSE STATUS'] = f'{url} ---- {resp.status}'

    # get rid of parts of URL that are irrelevant or could lead to traps
    url_no_fragment = sanitize_url(url)

    # status 200 means we retrieved webpage succesfully and we haven't crawled it yet
    if resp.status == 200 and url_no_fragment not in unique_urls:
        # received webpage -> convert to beautifulsoup object containing just the content, lxml because it was the recommended parser
        soup = BeautifulSoup(resp.raw_response.content, 'lxml')

        # LOW INFO VALUE: Avoid webpages without less than one div because these commonly do not hold much valuable information
        if len(soup.find_all("div")) < 1:
            return []
        
        # retrieve all of the text from the webpage
        text = soup.get_text()
        
        # QUESTION 1 CODE: substring url to discard fragment and add to unique_urls
        unique_urls.add(url_no_fragment)
        output['QUESTION 1 : Number of Unique URLs'] = len(unique_urls)

        # QUESTION 2 CODE: tokenize the webpage to get the number of words and then determine if it is the longest webpage
        word_tokens = []
        
        # create tokenizer that separates based on groups of whitespace
        reg_tokenizer = RegexpTokenizer('\s+', gaps=True)

        # create a regex object to match nonalphanumeric characters so we can remove them later on
        alphanum_word = re.compile(r'\W')

        # iterate over all words that tokenizer returns
        for word in reg_tokenizer.tokenize(text):
            # if a word is not composed of only non-alphanumeric characters, or if it is greater than one character
            # then we want to keep it
            if not re.match(r'^(\W+|^[\w+])$', word):
                # remove all non-alphanumeric characters from the word
                sanitized_word = alphanum_word.sub("", word)

                # LOW INFO VALUE: if length of word is greater than 1, add to word_token list
                #                 we do this to retain only relevant words
                if len(sanitized_word) > 1: 
                    word_tokens.append(sanitized_word)

        # LOW INFO VALUE: if # of words is less than 150, consider as a low info page
        if len(word_tokens) < 150:
            return []
        
        # if current page's word token count is greater than what we have seen, then make it the longest page
        word_token_count = len(word_tokens)        
        if word_token_count > longest_page[1]:
            longest_page = (url, word_token_count)        
        
        # QUESTION 3 CODE: get the 50 most common words across all the pages crawled
        for word in word_tokens:
            # using a dictionary to count how many times the word appears in all pages
            if word.lower() not in stop_words:
                word_count[word.lower()] += 1
            else:
                # is a stop word and don't want to include in our tokens
                word_tokens.remove(word)

        if len(word_tokens) < 150:
            # LOW INFO VALUE: check again if, after removing any stop words, meets our threshold
            return []

        # sort words highest to lowest based off their frequency and take top 50
        frequency = sorted(word_count.items(), key = lambda f: f[1], reverse = True)
        common_50 = [w[0] for w in frequency[:50]]

        output['QUESTION 3: 50 Most Common Words'] = common_50

        # QUESTION 4 CODE: do regex check to see if anything before ics in ics.uci.edu, retrieve it, add to dict along w defragmented url
        # (https?:\/\/) : matches http with optional s and forward slash forward slash
        # (\w*\.?ics\.uci\.edu)+ : matches ics.uci.edu with optional alphanumeric characters (subdomain) + optional '.' in front in case there is subdomain
        # (.*) : matches anything or nothing afterwards in case there is a longer path
        parsed_url = re.search(r'(https?:\/\/)(\w*\.?ics\.uci\.edu)+(.*)', url_no_fragment)
        if parsed_url:
            # we get the subdomain and add to dictionary with the full de-fragmented url
            subdomain = parsed_url.group(2)
            subdomains[subdomain].add(url_no_fragment)

        # retrieve all valid links on page and return them (to be added to frontier)
        links = extract_next_links(url, resp)
        write_output(output)
        ret_links = [link for link in links if is_valid(link)]
        return ret_links
        
    return []

def extract_next_links(url, resp):
    # lxml is the recommended page parser from assignment spec -> faster than html.parser
    page_soup = BeautifulSoup(resp.raw_response.content, "lxml")
    # for all links (identifiable by the <a> tag), get the link and add to frontier
    # link.get('href') gets actual link from within the tag
    next_links = [link.get('href') for link in page_soup.find_all('a')]
    
    return next_links

def is_valid(url) -> bool:
    # if url is a none then its not valid
    if not url:
        return False

    try:
        # if we've visited the sanitized url already then it is not valid
        url_no_fragment = sanitize_url(url)
        if url_no_fragment in unique_urls:
            return False

        # make sure that the url has http(s) in the scheme
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        # parsed.netloc is the domain of the url
        # if the domain is within the list of valid urls
        # and the url does not end with one certain paths we want to avoid
        # and the url is not in a folder of the paths that we don't want to look at
        return re.search(r"(ics.uci.edu|cs.uci.edu|informatics.uci.edu|stat.uci.edu)", parsed.netloc.lower()) is not None and not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4|Z|odc"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1|nb|txt"
            + r"|thmx|mso|arff|rtf|jar|csv|ppsx|img"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()) and re.search(
            r"\/(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4|Z|odc"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1|nb|txt|uploads"
            + r"|thmx|mso|arff|rtf|jar|csv|ppsx|img"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)\/", parsed.path.lower()) is None

    except TypeError:
        print ("TypeError for ", parsed)
        raise

def sanitize_url(url):
    # cleans up the url, excluding unnecessary portions
    url_no_fragment = url.split('#')[0] # we don't want the fragment -> leads to same page
    # all the below queries lead to traps -> based off inspection
    url_no_fragment = url_no_fragment.split("/?replytocom=")[0]
    url_no_fragment = url_no_fragment.split("/?share=")[0]
    url_no_fragment = url_no_fragment.split("/?ical=")[0]
    url_no_fragment = url_no_fragment.split("?do=")[0]
    url_no_fragment = url_no_fragment.split("?action=")[0]
    url_no_fragment = url_no_fragment.split("?version=")[0]
    url_no_fragment = url_no_fragment.split("?afg")[0]
    
    # if the url is not none and the last char in the url string is a forwardslash -> remove since it gave duplicates
    if url_no_fragment and url_no_fragment[-1] == "/":
        url_no_fragment = url_no_fragment[:-1]

    return url_no_fragment

def write_output(output_dict):
    with open('output.txt', 'a') as file:

        # for number 1
        for k,v in output_dict.items():
            file.write(k+'\t')
            file.write(str(v)+"\n")
        
        # for number 2
        file.write('QUESTION 2 : Longest Webpage\n')
        file.write(longest_page[0]+"\t")
        file.write(str(longest_page[1])+"\n")

        file.write('QUESTION 4: Subdomains and Number of Pages Within\n')
        for k,v in sorted(subdomains.items()):
            file.write(k+"\t")
            file.write(str(len(v))+"\n")
        
        file.write("-----------------------------------\n")

    if len(unique_urls) > 6000:
        with open("unique_urls.txt", "a") as f:
            f.write(str(unique_urls)+'\n')
            f.write("-----------------------------------------------------\n")