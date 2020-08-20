import sqlite3
from datetime import date
from myconfig import database

def addQuarter(qid, name):        
        conn = sqlite3.connect(database)
        c = conn.cursor()

        try:
                c.execute("INSERT INTO QuarterTable VALUES (:qID, :qName)", {'qID': qid, 'qName': name})
        except sqlite3.IntegrityError:
                pass

        conn.commit()

        conn.close()

def addCourse(codeVar, courseNumberVar, daysVar, passVar, fullVar, qid):
        #nameVar = str((nameVar.replace(u'\xa0', ' ').replace(u'\-xa0',' '))) # fixes unicode space

        if(fullVar == False): # if the course is not full
                daysVar = None
                passVar = None

        conn = sqlite3.connect(database)
        c = conn.cursor()

        try:
                c.execute("INSERT INTO CourseTable (courseCode, courseNumber, daysSincePass, passNumber, full, quarterID) \
                                        VALUES (:courseCode, :courseNumber, :daysSincePass, :passNumber, :full, :quarterID)", \
                        {'courseCode': codeVar, \
                        'courseNumber': courseNumberVar, \
                        'daysSincePass': daysVar, \
                        'passNumber': passVar, \
                        'full': fullVar, \
                        'quarterID': qid})
        except sqlite3.IntegrityError: # catches duplicates
            conn.close()

            if(fullVar): # only update if full
                updateCourse(codeVar, courseNumberVar, daysVar, passVar, fullVar, qid)

            return

        conn.commit()

        conn.close()

def addPass(passNumber, startVar, endVar, qid):
        conn = sqlite3.connect(database)
        c = conn.cursor()

        try:
                c.execute("INSERT INTO PassTable (pass, startDate, endDate, quarterID) \
                                        VALUES (:pass, :startDate, :endDate, :quarterID)", \
                        {'pass': passNumber, \
                        'startDate': startVar, \
                        'endDate': endVar, \
                        'quarterID': qid})
        except sqlite3.IntegrityError: # catches duplicates
            conn.close()
            updatePass(passNumber, startVar, endVar, qid)
            return

        conn.commit()

        conn.close()

def createQuarterTable():
        conn = sqlite3.connect(database)

        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS QuarterTable
                (quarterID     INTEGER NOT NULL    UNIQUE, 
                quarterName   TEXT    NOT NULL    UNIQUE);''')


        conn.close()

def createCourseTable():
        conn = sqlite3.connect(database)

        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS CourseTable
                (courseTableID INTEGER NOT NULL PRIMARY KEY, 
                courseCode     TEXT    NOT NULL,
                courseNumber   TEXT    NOT NULL,
                daysSincePass  INTEGER,
                passNumber     INTEGER,
                full           INTEGER,
                quarterID      INTEGER,
                FOREIGN KEY (quarterID) REFERENCES QuarterTable (quarterID),
                UNIQUE(courseCode, courseNumber, quarterID));''') # prevents duplicates


        conn.close()

        initFullTrigger()

def createPassTable():
        conn = sqlite3.connect(database)

        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS PassTable
                (passTableID INTEGER NOT NULL PRIMARY KEY,
                pass         INTEGER NOT NULL,
                startDate    TEXT,
                endDate      TEXT,
                quarterID    INTEGER,
                FOREIGN KEY (quarterID) REFERENCES QuarterTable (quarterID),
                UNIQUE(pass, quarterID));''') # prevents duplicates


        conn.close()


def updatePass(passNumber, startVar, endVar, qid):
        conn = sqlite3.connect(database)

        c = conn.cursor()

        c.execute('''UPDATE PassTable
                        SET startDate = :startDate,
                            endDate = :endDate
                        WHERE pass = :pass AND quarterID = :quarterID;''', \
                {'startDate': startVar, \
                 'endDate': endVar, \
                 'pass': passNumber, \
                 'quarterID': qid \
                 })

        conn.commit()

        conn.close()

def updateCourse(codeVar, courseNumberVar, daysVar, passVar, fullVar, qid):
        conn = sqlite3.connect(database)

        c = conn.cursor()

        try:
                c.execute('''UPDATE CourseTable
                                SET daysSincePass = :daysSincePass,
                                passNumber = :passNumber,
                                full = :full
                                WHERE courseCode = :courseCode AND courseNumber = :courseNumber AND quarterID = :quarterID;''', \
                        {'daysSincePass': daysVar, \
                        'passNumber': passVar, \
                        'full': fullVar, \
                        'courseCode': codeVar, \
                        'courseNumber': courseNumberVar, \
                        'quarterID': qid \
                        })
        except sqlite3.IntegrityError:
                conn.close()
                return


        conn.commit()

        conn.close()

def printAll():
        conn = sqlite3.connect(database)

        c = conn.cursor() 

        c.execute('''SELECT * FROM CourseTable''')

        rows = c.fetchall()

        for row in rows:
                print(row)

        conn.close()

def getPassDates(incomingQuarter):
        conn = sqlite3.connect(database)

        c = conn.cursor() 

        c.execute('''SELECT * FROM PassTable
                     WHERE quarterID = :quarterID''', {'quarterID': incomingQuarter})

        rows = c.fetchall()

        # for row in rows:
        #         print(row[2])

        conn.close()
        return rows

# removes chosen table
def deleteTable(tableName):
        conn = sqlite3.connect(database)

        c = conn.cursor()

        c.execute('DROP TABLE [IF EXISTS] :table', {'table': tableName})


        conn.close()


# removes all tables
def clearTables():
        conn = sqlite3.connect(database)

        c = conn.cursor()

        c.execute('DROP TABLE IF EXISTS PassTable')
        c.execute('DROP TABLE IF EXISTS CourseTable')
        c.execute('DROP TABLE IF EXISTS QuarterTable')


        conn.close()

def getCurrentPass(incomingQuarter):
        passDates = getPassDates(incomingQuarter)

        today = date.today()
        #today = date(2020, 5, 29)

        currentPass = None
        for i in range(0,3):
                passStartStr = passDates[i][2]
                passStart = date(int("20" + passStartStr[-2:]), int(passStartStr[:2]), int(passStartStr[3:5]))
                passEndStr = passDates[i][3]
                passEnd = date(int("20" + passEndStr[-2:]), int(passEndStr[:2]), int(passEndStr[3:5]))
                if(passStart <= today <= passEnd):
                        currentPass = i + 1

        return currentPass

def getDaysSincePass(incomingQuarter, passNumber):
        
        if(passNumber == None):
                return None
        
        passDates = getPassDates(incomingQuarter)

        today = date.today()
        #today = date(2020, 5, 29)


        passStartStr = passDates[passNumber - 1][2]
        passStart = date(int("20" + passStartStr[-2:]), int(passStartStr[:2]), int(passStartStr[3:5]))

        daysSince = (today-passStart).days

        return daysSince

# makes full courses read only
def initFullTrigger():
        conn = sqlite3.connect(database)

        c = conn.cursor()
        #c.execute("DROP TRIGGER FullStop")
        c.execute('''CREATE TRIGGER IF NOT EXISTS FullStop
        BEFORE UPDATE ON CourseTable
        BEGIN
                SELECT CASE WHEN NEW.full = OLD.full
                        THEN RAISE (ABORT,'Nothing New')
                END;
        END;''')

        conn.close()
