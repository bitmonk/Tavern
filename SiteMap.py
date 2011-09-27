#!/opt/local/bin/python
import datetime
import pymongo
from bson.code import Code
from server import server
from User import User
from pprint import pprint
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-m", "--messagestart",
                  action="store", type="int", dest="start", default=0,
                  help="The message to start the counting at.")
parser.add_option("-f", "--filestart", 
                  action="store", type="int", dest="sitestart", default=0,
                  help="The sitemap file to begin at.")

(options, args) = parser.parse_args()

countEnvelopes = server.mongos['default']['envelopes'].find({"envelope.payload.class": "message"}).count()

divisor = 40000
start = options.start
end = start + divisor - 1
if end > countEnvelopes:
    end = countEnvelopes
    
sitemapcount = 1 + (countEnvelopes / divisor)

print "This will generate " + str(sitemapcount) + " sitemaps, beginning with element " + str(start)
print "Generating Master sitemap file"

date1  = datetime.datetime.now().isoformat()
datenow = date1[0:date1.find(".")] + "+00:00"

sitemapindex = open('static/sitemaps/sitemap_index.xml', 'w')
sitemapindex.write("""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/siteindex.xsd" xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap>
<loc>http://ForumLegion.com/static/sitemaps/sitemap-0.xml</loc>
<lastmod>""" + datenow + """</lastmod>
</sitemap>""")

for i in range(sitemapcount):
    sitemap_path = "static/sitemaps/sitemap-" + str(i + 1) + ".xml"
    sitemap = open(sitemap_path, 'w')  
    sitemap.write("""<?xml version="1.0" encoding="UTF-8"?>\n""")
    sitemap.write("""<urlset xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd" xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n""")
    print "Starting file " + str(i) + "; start = " + str(start) + " ; end " + str()

 
    sitemapindex.write("<sitemap>")
    sitemapindex.write("<loc>http://ForumLegion.com/static/sitemaps/sitemap-" + str(i + 1) + ".xml</loc>\n")
    sitemapindex.write("<lastmod>" + datenow +  "</lastmod>\n")
    sitemapindex.write("</sitemap>\n")
    
    a = server.mongos['default']['envelopes'].find()[start:end]
    for envelope in a:
        url = 'http://ForumLegion.com/message/' + envelope['envelope']['payload_sha512']
        date = datetime.datetime.utcfromtimestamp(envelope['envelope']['stamps'][0]['time_added'])
        datestr = date.isoformat()
        datecur = datestr[0:datestr.find(".")] + "+00:00"
        sitemap.write("<url>\n")
        sitemap.write("<loc>" + url + "</loc>\n")
        sitemap.write("<lastmod>" + datecur + "</lastmod>\n")
        sitemap.write("<changefreq> monthly </changefreq>\n")   
        sitemap.write("<priority> .5 </priority>\n")
        sitemap.write("</url>\n")
    sitemap.write("</urlset>\n")
    sitemap.close()

    start = start + 40000
    end = start + divisor - 1
    if end > countEnvelopes:
        end = countEnvelopes
    
sitemapindex.write("</sitemapindex>\n")
sitemapindex.close()

# print "Notifying Bing"
# cmd = 'curl http://www.bing.com/webmaster/ping.aspx?siteMap=http://lonava.com/static/sitemaps/sitemap_index.xml > /dev/null'
# os.system(cmd)
# print "Notifying Google"
# cmd = 'curl http://www.google.com/webmasters/sitemaps/ping?sitemap=http://lonava.com/static/sitemaps/sitemap_index.xml > /dev/null'
# os.system(cmd)