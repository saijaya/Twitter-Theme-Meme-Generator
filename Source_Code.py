# Sai J
# This script is meant to
# 1. Collect Tweets from Twitter API
# 2. Process the API response, collect tweets
# 3. Find the most important word in the tweets
# 4. Access Giphy API and find meme for the word and collect the gif URL
# 5. Make html file with the image.
# I'm using iPython notebook to avoid hitting Twitter API Rate limit.

from __future__ import division #For float division
import random

import tweepy #Package to handle Twitter API
import json
import unicodedata
from nltk.tag import pos_tag #Find Part of Speech (POS) in text
from nltk import word_tokenize
from nltk.corpus import stopwords
from nltk.corpus import words
from collections import Counter

import requests #To access Giphy API

from django.template import Template, Context
from django.conf import settings
# Run this if settings now configured. Run only once per session
settings.configure()

# Function to Authorize API Access and return authorized API class object
def twitter_auth(consumer_key, consumer_secret,access_token, access_token_secret):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    return api

# Use the API class object to access timeline of user specified by user_name
def get_response(api, user_name, num_tweets):
    response = api.user_timeline(id = user_name, count = num_tweets)
    return response

# Process the API response for Analysis.
# Returns a dictionary of the words in tweets
def vectorize_response(response, num_tweets):
    english = words.words() #List of all words in English language
    tweet_vector = []
    word_vector = []
    keyword_dict = {}
    stop = stopwords.words('english') #List of stop-words in English
    
    for i in range(num_tweets): 
        #Convert to JSON and get the text of the tweet
        tweet_vector.append(unicodedata.normalize('NFKD', json.loads(json.dumps(response[i]._json))['text']).encode('ascii','ignore'))
    tweet_vector = [word_tokenize(x) for x in tweet_vector] #Tokenize the tweets and save each tweet as bag of words (Vector of words)
    for x in tweet_vector: #For each tweet vector
        #Get Only Aplhabetic tokens, Get only English words and remove stop words
        keywords = [w for w in [z for z in [y for y in x if y.isalpha()] if z.lower() not in stop] if w in english]
        #Retain only certain parts of speech in content: Adjective, Adverb, Noun, Interjection
        # I think these parts of speech have the most informative value in tweets
        imp_pos = ['JJ','JJS','RB','RBS','NN', 'NNP', 'NNS', 'NNPS', 'UH']
        POS = [word for word,pos in pos_tag(keywords) if pos in imp_pos] 
        word_vector.append(POS)
    keywords = Counter(sum(word_vector,[])) #Convert the entire bag of words into a dictionary with frequency of words as value
    return keywords

# Functionc combining the above two functions
def get_words(api, user_name, num_tweets):
    response = get_response(api,user_name, num_tweets)
    keywords = vectorize_response(response,num_tweets)
    return keywords


# Frequently used words in English.
# It's a .txt file which has the frequency of words against frequently-used words in English.
# Function makes a frequency dictionary of words we are interested in.
def get_word_freq(keywords):
    f = open('word_frequency.txt', 'r')
    word_frequency = f.readlines()
    word_freq_dict = {}
    word_frequency = [x for x in word_frequency if x.split()[2] in keywords] # Get words we are interested in (From the tweets)
    for i in range(len(word_frequency)):
        word_freq_dict[word_frequency[i].split()[2]] = int(word_frequency[i].split()[1]) #Get frequency of those words
    return word_freq_dict

#Proper nouns in the tweets that are not frequently used (As per the English word Frequency file)
def get_rare_nouns(keywords,word_freq_dict):
    Nouns  = [x for x,p in pos_tag([w for w in keywords if w not in word_freq_dict]) if p in ['NNP']]
    return Nouns

#Get the most important word from the tweets based on Context & Word Frequency File
# Returns the most important word
def get_imp_word(consumer_key, consumer_secret, access_token, access_token_secret, user_name, num_tweets):
    api = twitter_auth(consumer_key, consumer_secret, access_token, access_token_secret)
    keywords = get_words(api, user_name, num_tweets)
    word_freq_dict = get_word_freq(keywords)
    context = get_words(api, user_name, 10*num_tweets) #Get the bag of words from last 100 tweets
    Nouns = get_rare_nouns(keywords,word_freq_dict) # Get Proper nouns that are not frequently used in English.
    new = [] #List for words not seen in the last 100 tweets, but seen in the recent 10 tweets
    jump = {} # Dictionary for words already used in past tweets
    for key in Nouns:
        if key not in context.keys():
            new.append(key)
        else:
            jump[key] = keywords[key]/context[key] # Get ratio of occurrence of the words in the last 10 days and last 100 days
    if len(new) <> 0: # If completely new Nouns have been used
        important_word = random.choice(new) # Choose one of them as the most important word
    else:
        important_word = max(jump, key=jump.get) # Otherwise, choose the word with greatest lift in usage since past tweets
    return important_word


# Search on giphy API for the word.
# Process the response and get MEME image url
def search_giphy(important_word, giphy_api_key):
    giphy_api_request = "http://api.giphy.com/v1/gifs/search?q={0}&api_key={1}&limit=1".format(important_word, giphy_api_key)
    giphy_response = requests.get(giphy_api_request).json() #Convert response to JSON object
    url = unicodedata.normalize('NFKD',giphy_response['data'][0]['images']['downsized']['url']).encode('ascii','ignore')
    height = int(unicodedata.normalize('NFKD',giphy_response['data'][0]['images']['downsized']['height']).encode('ascii','ignore'))
    width = int(unicodedata.normalize('NFKD',giphy_response['data'][0]['images']['downsized']['width']).encode('ascii','ignore'))
    return url, height, width


# Generate HTML file with the gif 
def generate_html(title, important_word, url, height, width):
    template = """
    <!DOCTYPE html>
    <html>
        <head>
            <title> {{ title }} 
            </title>
        </head>
        <body>
            <h3>
            {{ important_word }}
            </h3>
            <img src = "{{ url }}" width="{{ width }}" height="{{ height }}" />
        </body>
        </html>
    """
    t = Template(template)
    c = Context({"title": title,
                 "important_word": important_word,
                 "url": url,
                 "width": width,
                 "height": height})
    f = open('{0}.html'.format(title), 'w')
    f.write(t.render(c))
    f.close()
    return



# Get most important word
important_word = get_imp_word(consumer_key, consumer_secret, access_token, access_token_secret, user_name, num_tweets)
print "The most important word in the last {0} tweets of {1} was: '{2}'".format(num_tweets, user_name, important_word)
url, height, width = search_giphy(important_word, giphy_api_key)
generate_html(title, important_word, url, height, width)
