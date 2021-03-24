from myconfig import username, password
from functions import *
import re # for character filtering
import sys # for sys.exit
import time # for execution time tests
import requests
from bs4 import BeautifulSoup
from courseCodes import *
from tqdm import tqdm # for progress bar


# set up session
print("Getting pass times")
session = requests.Session()
url = 'https://registrar.sa.ucsb.edu/calendars/calendars-deadlines/registration-pass-dates/'
currentPage = session.get(url)
soup = BeautifulSoup(currentPage.content, 'html.parser')

# init tables
#clearTables()
createQuarterTable()
createCourseTable()
createPassTable()

# set up pass time table
startDate = ""
endDate = ""
tables = soup.find_all('tbody') # 3 sets of pass times
for qID in range(1,4):
    rows = tables[qID - 1].find_all('tr')
    label = rows[0].find('th', attrs={'class': 'tg-loew'}).getText() #  quarter name

    quarterKey = re.sub("[^a-zA-Z]+", "", label) # removes non-alphabet chars
    year = re.sub("[^0-9]+", "", label) # removes non-numeric chars

    qid = int(year + quarterCodes[quarterKey]) # formats quarter ID

    addQuarter(qid, label)

    # delete non-passtime entries
    del rows[0:4]
    del rows[5:13]

    # adds pass time date to table
    for passNum in range(1,4):
        startDate = rows[(2 * passNum) - 2].find('td', attrs={'class': 'tg-baqh'})
        startDate = startDate.getText()
        sep = " - "
        startDate = startDate.split(sep, 1)[0]

        endDate = rows[(2 *  passNum) - 1].find('td', attrs={'class': 'tg-baqh'})
        endDate = endDate.getText()        
        
        # change empty date formatting
        if(startDate == ''):
            startDate = None
        if(endDate == ''):
            endDate = None
        
        addPass(passNum, startDate, endDate, qid)




print("Logging in to GOLD")

payload = {
    "__VIEWSTATE": "",
    "__VIEWSTATEGENERATOR": "",
    "__EVENTVALIDATION": "",
	"ctl00$pageContent$userNameText": username, 
	"ctl00$pageContent$passwordText": password,
    "ctl00$pageContent$loginButton": "Login"
}

# updates url to Gold login
url = "https://my.sa.ucsb.edu/gold/Login.aspx"




# sets payload
currentPage = session.get(url)
soup = BeautifulSoup(currentPage.content, 'html.parser')
payload['__VIEWSTATE'] = soup.find(id="__VIEWSTATE")["value"]
payload['__VIEWSTATEGENERATOR'] = soup.find(id="__VIEWSTATEGENERATOR")["value"]
payload['__EVENTVALIDATION'] = soup.find(id="__EVENTVALIDATION")["value"]



# logs in with payload form data
currentPage = session.post(url, payload)
soup = BeautifulSoup(currentPage.content, 'html.parser')

# catches bad login data
if soup.find(string="Announcements") == None:
    sys.exit("Bad password/username")
else:
    print("Login successful!")

# updates url to Find Courses page
url = "https://my.sa.ucsb.edu/gold/BasicFindCourses.aspx"

# navigates to Find Courses page
currentPage = session.get(url)
soup = BeautifulSoup(currentPage.content, 'html.parser')


# gets incoming quarter as q
quarterDropDown = soup.find('select', attrs={'name': 'ctl00$pageContent$quarterDropDown'})
incomingQuarter = quarterDropDown.find('option')
if(incomingQuarter['value'][-1] == '3'): # if Summer
    incomingQuarter = incomingQuarter.findNext('option')
q = incomingQuarter['value']


# updates payload for Find Course page
payload = {
    "__VIEWSTATE": "",
    "__VIEWSTATEGENERATOR": "",
    "ctl00$pageContent$quarterDropDown": q,
    "ctl00$pageContent$subjectAreaDropDown": "",
    "ctl00$pageContent$searchButton": "submit"
}

# variables relevant to courses
isFull = False
courseName = ""
courseNumber = ''

# iterates over subjects
print("Scanning all courses for incoming quarter...")
for key in tqdm(subjectCodes):
    soup = BeautifulSoup(currentPage.content, 'html.parser')

    # sets payload variables
    payload["ctl00$pageContent$subjectAreaDropDown"] = subjectCodes[key]
    payload['__VIEWSTATE'] = soup.find(id="__VIEWSTATE")["value"]
    payload['__VIEWSTATEGENERATOR'] = soup.find(id="__VIEWSTATEGENERATOR")["value"]

    # loads course search
    currentPage = session.post(url, payload)
    while soup.find(string="course # (optional)") != None:
        soup = BeautifulSoup(currentPage.content, 'html.parser')

    # determine which courses are full
    openSections = False
    table = soup.find('div', attrs={'class': "datatableNew"})
    children = table.find_all('div')

    # addresses subjects with no courses offered
    try:
        header = children[0]['class']
    except IndexError:
        currentPage = session.get(url)
        continue

    # iterates through course headers and lectures
    for child in children:
        isFull = False
        if(child['class'] == header): #  if  element is a header
            # sets "full" status
            if(children[0] != child): 
                if(openSections == False):
                    isFull = True
                
                addCourse(subjectCodes[key], courseNumber, getDaysSincePass(q, getCurrentPass(q)), getCurrentPass(q), isFull, int(q))
                
            openSections = False

            # format course name to course number
            courseName = child.find('span', attrs={'class': "courseTitle"}).getText()
            courseName = str((courseName.replace(u'\xa0', ' ').replace(u'\-xa0',' '))) # fixes unicode space
            sep = ' - '
            left = courseName.split(sep, 1)[0]
            mid = left.split(subjectCodes[key], 1)[1] 
            courseNumber = re.sub(' +', ' ', mid.strip()) # remove whitespace on ends and duplicate spaces

        elif(child['class'] == ['courseSearchItem']): # if element is a lecture
            spaces = child.find_all('div', attrs={'class': "col-lg-search-space"}) # list of space elements

            # lecture space
            lecture = spaces[0] 
            parsedLectureSpace = (re.sub('\ |\Space', '', lecture.getText())).replace('\n', '')

            # creates list for space in each section
            sections = iter(spaces)
            next(sections, None)

            if(parsedLectureSpace != '\rFull\r'): # if the lecture is open
                for section in sections:
                    parsedSectionSpace = (re.sub('\ |\Space', '', section.getText())).replace('\n', '')

                    if(parsedLectureSpace != '\rFull\r'): # if any section is open
                        openSections = True
                        break

                if(len(spaces) == 1): # if there are no sections
                    openSections = True
    
    # sets "full" status of last course
    if(openSections == False):
        isFull = True

    # last course in subject
    addCourse(subjectCodes[key], courseNumber, getDaysSincePass(q, getCurrentPass(q)), getCurrentPass(q), isFull, int(q)) 
    
    # returns to Find Courses Page
    currentPage = session.get(url)
print("Done.")

x = input("Would you like to view the database? (y/n) ")

if(x == 'y'):
    print("Printing database")
    print("in form ['databaseID', 'courseCode', 'courseNumber', 'daysSincePass', 'passNumber', 'fullStatus', 'quarterID']...")
    time.sleep(10)

    printAll()




