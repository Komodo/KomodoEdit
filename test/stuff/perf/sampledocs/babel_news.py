import sys
import string
import WebService

reload(sys)
sys.setdefaultencoding("latin-1")

def scrapeHeadlines(text):
    headlines = "";
    lines = text.splitlines()
    for line in lines:
        if (string.find(line, "<a href") == 0):
            pos1 = string.find(line, "<b>")
            if pos1 > 0:
                pos2 = string.find(line, "</b>")
                if pos2 > 0:
                    headlines += line[pos1+len("<b>"):pos2] + ".\n"
    return headlines
    
print '--- Creating Headline Web Service'
news_service = WebService.ServiceProxy("http://www.soapclient.com/xml/SQLDataSoap.WSDL");
print '--- Calling Headline Web Service'
news = news_service.ProcessSRL("NEWS.SRI", "yahoo", "");
headlines = scrapeHeadlines(news)
print '--- Got headlines in English'
print headlines

print '--- Creating Translation Web Service'
babel_service = WebService.ServiceProxy("http://www.xmethods.net/sd/BabelFishService.wsdl");
print '--- Calling Translation Web Service'
translation = babel_service.BabelFish("en_fr", headlines)
print '--- Translated headlines:'
print translation
print '--- Done!'
