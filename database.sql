BEGIN TRANSACTION;
CREATE TABLE requests (
        request_id TEXT PRIMARY KEY,
        student_id TEXT,
        query TEXT,
        category TEXT,
        technician TEXT,
        start_time TEXT,
        end_time TEXT,
        assigned_time TEXT,
        student_free_time TEXT,
        status TEXT
    );
CREATE TABLE students (
        student_id TEXT PRIMARY KEY,
        name TEXT,
        password TEXT
    );
INSERT INTO "students" VALUES('1001','Shashwat','123');
INSERT INTO "students" VALUES('1002','Rohan','123');
INSERT INTO "students" VALUES('101','Shashwat Dubey','1234');
INSERT INTO "students" VALUES('102','Ravi Kumar','1234');
INSERT INTO "students" VALUES('103','Aman Singh','1234');
CREATE TABLE technicians (
        name TEXT PRIMARY KEY,
        role TEXT,
        start_time TEXT,
        end_time TEXT,
        current_load INTEGER DEFAULT 0,
        status TEXT DEFAULT 'free',
        password TEXT
    );
INSERT INTO "technicians" VALUES('Ravi','electrician','9','18',0,'free','123');
INSERT INTO "technicians" VALUES('Suresh','plumber','10','17',0,'free','123');
INSERT INTO "technicians" VALUES('Amit','carpenter','11','19',0,'free','123');
INSERT INTO "technicians" VALUES('Ramesh','electrician','9','18',0,'free','1234');
INSERT INTO "technicians" VALUES('Mahesh','carpenter','9','17',0,'free','1234');
COMMIT;
